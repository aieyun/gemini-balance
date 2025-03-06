# app/services/chat/api_client.py

from typing import Dict, Any, AsyncGenerator
import httpx
import asyncio
from abc import ABC, abstractmethod


class ApiClient(ABC):
    """API客户端基类"""

    @abstractmethod
    async def generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def stream_generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> AsyncGenerator[str, None]:
        pass


class GeminiApiClient(ApiClient):
    """Gemini API客户端"""

    def __init__(self, base_url: str, timeout: int = 300):
        self.base_url = base_url
        # 配置不同操作的超时时间
        self.timeout = httpx.Timeout(
            connect=10.0,    # 连接超时
            read=timeout,    # 读取超时
            write=30.0,      # 写入超时
            pool=5.0         # 连接池获取连接超时
        )
        # 配置重试策略
        self.max_retries = 3
        self.retry_delay = 1.0  # 初始重试延迟（秒）

    def _prepare_model_name(self, model: str) -> str:
        """准备模型名称，移除搜索后缀"""
        if model.endswith("-search"):
            return model[:-7]
        return model

    async def generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        if model.endswith("-search"):
            model = model[:-7]
        async with httpx.AsyncClient(timeout=timeout) as client:
            url = f"{self.base_url}/models/{model}:generateContent?key={api_key}"
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                error_content = response.text
                raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
            return response.json()

    async def stream_generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> AsyncGenerator[str, None]:
        """流式生成内容"""
        model = self._prepare_model_name(model)
        url = f"{self.base_url}/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
        
        # 实现异步重试逻辑
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(method="POST", url=url, json=payload) as response:
                        response.raise_for_status()  # 抛出HTTP错误
                        async for line in response.aiter_lines():
                            yield line
                        # 成功完成，退出循环
                        return
            except httpx.HTTPStatusError as e:
                error_content = await e.response.aread()
                error_msg = error_content.decode("utf-8")
                if attempt == self.max_retries - 1:  # 最后一次尝试
                    raise Exception(f"API call failed with status code {e.response.status_code}: {error_msg}")
                # 异步指数退避重试
                retry_delay = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(retry_delay)
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:  # 最后一次尝试
                    raise Exception(f"Request error: {str(e)}")
                # 异步指数退避重试
                retry_delay = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(retry_delay)
            except Exception as e:
                if attempt == self.max_retries - 1:  # 最后一次尝试
                    raise Exception(f"Unexpected error: {str(e)}")
                # 异步指数退避重试
                retry_delay = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(retry_delay)
