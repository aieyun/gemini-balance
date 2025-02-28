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
        try:
            for key in api_keys:
                stmt = select(APIKey).where(APIKey.key == key)
                result = await self.db.execute(stmt)
                existing_key = result.scalar_one_or_none()
                
                if not existing_key:
                    new_key = APIKey(key=key)
                    self.db.add(new_key)
            
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error initializing keys: {str(e)}")
            await self.db.rollback()
            # 如果是唯一键冲突，我们可以忽略它，因为这意味着key已经存在
            if "Duplicate entry" not in str(e):
                raise

    async def get_next_key(self) -> str:
        """获取下一个API key"""
        async with self.key_cycle_lock:
            stmt = select(APIKey).where(APIKey.status is True) 
            result = await self.db.execute(stmt)
            valid_keys = result.scalars().all()
            
            if not valid_keys:
                logger.error("No valid API keys available")
                raise Exception("No valid API keys available")
            
            self._current_key_index = (self._current_key_index + 1) % len(valid_keys)
            return valid_keys[self._current_key_index].key

    async def is_key_valid(self, key: str) -> bool:
        """检查key是否有效"""
        stmt = select(APIKey).where(APIKey.key == key)
        result = await self.db.execute(stmt)
        key_record = result.scalar_one_or_none()
        return key_record and key_record.status and key_record.failure_count < self.MAX_FAILURES

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
                    logger.warning(f"API key {api_key} has failed {self.MAX_FAILURES} times and is now disabled")
                await self.db.commit()
                logger.info(f"Increased failure count for API key {api_key} to {key_record.failure_count}")
            else:
                logger.warning(f"API key {api_key} not found in database")

        return await self.get_next_working_key()

    async def get_next_working_key(self) -> str:
        """获取下一个可用的API key"""
        # 记录尝试过的所有key，避免无限循环
        tried_keys = set()
        
        try:
            initial_key = await self.get_next_key()
            current_key = initial_key
            tried_keys.add(current_key)
            
            while True:
                if await self.is_key_valid(current_key):
                    return current_key
                
                current_key = await self.get_next_key()
                if current_key in tried_keys:
                    # 所有key都尝试过且无效
                    logger.error("All API keys have been tried and none are valid")
                    raise Exception("No valid API keys available")
                tried_keys.add(current_key)
        except Exception as e:
            logger.error(f"Error in get_next_working_key: {str(e)}")
            # 如果所有key都无效，尝试重置所有key的失败计数
            await self.reset_failure_counts()
            logger.info("Reset all API keys failure counts due to no valid keys available")
            # 再次尝试获取key
            return await self.get_next_key()

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
        try:
            stmt = update(APIKey).values(failure_count=0, status=True)
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info("Successfully reset all API keys failure counts")
        except Exception as e:
            logger.error(f"Error resetting failure counts: {str(e)}")
            raise
            
    async def get_paid_key(self) -> str:
        """获取付费key"""
        if settings.PAID_KEY:
            # 确保付费key在数据库中
            stmt = select(APIKey).where(APIKey.key == settings.PAID_KEY)
            result = await self.db.execute(stmt)
            key_record = result.scalar_one_or_none()
            
            if not key_record:
                # 如果付费key不在数据库中，添加它
                new_key = APIKey(key=settings.PAID_KEY)
                self.db.add(new_key)
                await self.db.commit()
                logger.info("Added paid key to database")
            
            return settings.PAID_KEY
        else:
            # 如果没有配置付费key，使用普通key
            logger.warning("No paid key configured, using regular key instead")
            return await self.get_next_working_key()

# 单例模式实现
_singleton_instance = None
_singleton_lock = asyncio.Lock()
_db_session = None

async def get_key_manager_instance(api_keys: list = None) -> KeyManager:
    global _singleton_instance, _db_session
    
    from app.database import AsyncSessionLocal
    
    async with _singleton_lock:
        if _singleton_instance is None:
            # 创建数据库会话并保持它的引用
            _db_session = AsyncSessionLocal()
            db = await _db_session.__aenter__()
            
            _singleton_instance = KeyManager(db)
            # 初始化数据库中的keys
            if api_keys:
                await _singleton_instance.initialize_keys(api_keys)
            else:
                await _singleton_instance.initialize_keys(settings.API_KEYS)
        return _singleton_instance
