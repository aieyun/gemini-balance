import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.api_key import APIKey
from app.core.config import settings
from app.core.logger import get_key_manager_logger

logger = get_key_manager_logger()

class KeyManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.key_cycle_lock = asyncio.Lock()
        self.failure_count_lock = asyncio.Lock()
        self.MAX_FAILURES = settings.MAX_FAILURES
        self._current_key_index = 0

    async def initialize_keys(self, api_keys: list):
        """初始化数据库中的API keys"""
        for key in api_keys:
            stmt = select(APIKey).where(APIKey.key == key)
            result = await self.db.execute(stmt)
            existing_key = result.scalar_one_or_none()
            
            if not existing_key:
                new_key = APIKey(key=key)
                self.db.add(new_key)
        
        await self.db.commit()

    async def get_next_key(self) -> str:
        """获取下一个API key"""
        async with self.key_cycle_lock:
            stmt = select(APIKey).where(APIKey.status == True)
            result = await self.db.execute(stmt)
            valid_keys = result.scalars().all()
            
            if not valid_keys:
                raise Exception("No valid API keys available")
            
            self._current_key_index = (self._current_key_index + 1) % len(valid_keys)
            return valid_keys[self._current_key_index].key

    async def is_key_valid(self, key: str) -> bool:
        """检查key是否有效"""
        stmt = select(APIKey).where(APIKey.key == key)
        result = await self.db.execute(stmt)
        key_record = result.scalar_one_or_none()
        return key_record and key_record.failure_count < self.MAX_FAILURES

    async def handle_api_failure(self, api_key: str) -> str:
        """处理API调用失败"""
        async with self.failure_count_lock:
            stmt = select(APIKey).where(APIKey.key == api_key)
            result = await self.db.execute(stmt)
            key_record = result.scalar_one_or_none()
            
            if key_record:
                key_record.failure_count += 1
                if key_record.failure_count >= self.MAX_FAILURES:
                    key_record.status = False
                    logger.warning(f"API key {api_key} has failed {self.MAX_FAILURES} times")
                await self.db.commit()

        return await self.get_next_working_key()

    async def get_next_working_key(self) -> str:
        """获取下一个可用的API key"""
        initial_key = await self.get_next_key()
        current_key = initial_key

        while True:
            if await self.is_key_valid(current_key):
                return current_key

            current_key = await self.get_next_key()
            if current_key == initial_key:
                # 所有key都无效时可以选择重置或抛出异常
                raise Exception("No valid API keys available")

    async def get_keys_by_status(self) -> dict:
        """获取分类后的API key列表"""
        stmt = select(APIKey)
        result = await self.db.execute(stmt)
        all_keys = result.scalars().all()
        
        valid_keys = {k.key: k.failure_count for k in all_keys if k.status}
        invalid_keys = {k.key: k.failure_count for k in all_keys if not k.status}
        
        return {
            "valid_keys": valid_keys,
            "invalid_keys": invalid_keys
        }

    async def reset_failure_counts(self):
        """重置所有key的失败计数"""
        stmt = update(APIKey).values(failure_count=0, status=True)
        await self.db.execute(stmt)
        await self.db.commit()

# 单例模式实现
_singleton_instance = None
_singleton_lock = asyncio.Lock()

async def get_key_manager_instance(db: AsyncSession = None) -> KeyManager:
    global _singleton_instance
    
    if not db:
        raise ValueError("Database session is required")
        
    async with _singleton_lock:
        if _singleton_instance is None:
            _singleton_instance = KeyManager(db)
            # 初始化数据库中的keys
            await _singleton_instance.initialize_keys(settings.API_KEYS)
        return _singleton_instance
