import requests
from app.schemas.image_models import ImageMetadata, ImageUploader, UploadResponse
from enum import Enum
from typing import Optional, Any


class UploadErrorType(Enum):
    """上传错误类型枚举"""
    NETWORK_ERROR = "network_error"  # 网络请求错误
    AUTH_ERROR = "auth_error"  # 认证错误
    INVALID_FILE = "invalid_file"  # 无效文件
    SERVER_ERROR = "server_error"  # 服务器错误
    PARSE_ERROR = "parse_error"  # 响应解析错误
    UNKNOWN = "unknown"  # 未知错误


class UploadError(Exception):
    """图片上传错误异常类"""

    def __init__(
            self,
            message: str,
            error_type: UploadErrorType = UploadErrorType.UNKNOWN,
            status_code: Optional[int] = None,
            details: Optional[dict] = None,
            original_error: Optional[Exception] = None
    ):
        """
        初始化上传错误异常
        
        Args:
            message: 错误消息
            error_type: 错误类型
            status_code: HTTP状态码
            details: 详细错误信息
            original_error: 原始异常
        """
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        self.original_error = original_error

        # 构建完整错误信息
        full_message = f"[{error_type.value}] {message}"
        if status_code:
            full_message = f"{full_message} (Status: {status_code})"
        if details:
            full_message = f"{full_message} - Details: {details}"

        super().__init__(full_message)

    @classmethod
    def from_response(cls, response: Any, message: Optional[str] = None) -> "UploadError":
        """
        从HTTP响应创建错误实例
        
        Args:
            response: HTTP响应对象
            message: 自定义错误消息
        """
        try:
            error_data = response.json()
            details = error_data.get("data", {})
            return cls(
                message=message or error_data.get("message", "Unknown error"),
                error_type=UploadErrorType.SERVER_ERROR,
                status_code=response.status_code,
                details=details
            )
        except Exception:
            return cls(
                message=message or "Failed to parse error response",
                error_type=UploadErrorType.PARSE_ERROR,
                status_code=response.status_code
            )


class SmMsUploader(ImageUploader):
    API_URL = "https://sm.ms/api/v2/upload"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def upload(self, file: bytes, filename: str) -> UploadResponse:
        try:
            # 准备请求头
            headers = {
                "Authorization": f"Basic {self.api_key}"
            }

            # 准备文件数据
            files = {
                "smfile": (filename, file, "image/png")
            }

            # 发送请求
            response = requests.post(
                self.API_URL,
                headers=headers,
                files=files
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析响应
            result = response.json()

            # 验证上传是否成功
            if not result.get("success"):
                raise UploadError(result.get("message", "Upload failed"))

            # 转换为统一格式
            data = result["data"]
            image_metadata = ImageMetadata(
                width=data["width"],
                height=data["height"],
                filename=data["filename"],
                size=data["size"],
                url=data["url"],
                delete_url=data["delete"]
            )

            return UploadResponse(
                success=True,
                code="success",
                message="Upload success",
                data=image_metadata
            )

        except requests.RequestException as e:
            # 处理网络请求相关错误
            raise UploadError(f"Upload request failed: {str(e)}")
        except (KeyError, ValueError) as e:
            # 处理响应解析错误
            raise UploadError(f"Invalid response format: {str(e)}")
        except Exception as e:
            # 处理其他未预期的错误
            raise UploadError(f"Upload failed: {str(e)}")


class QiniuUploader(ImageUploader):
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key

    def upload(self, file: bytes, filename: str) -> UploadResponse:
        # 实现七牛云的具体上传逻辑
        pass


class ImageUploaderFactory:
    @staticmethod
    def create(provider: str, **credentials) -> ImageUploader:
        if provider == "smms":
            return SmMsUploader(credentials["api_key"])
        elif provider == "qiniu":
            return QiniuUploader(
                credentials["access_key"],
                credentials["secret_key"]
            )
        raise ValueError(f"Unknown provider: {provider}")
