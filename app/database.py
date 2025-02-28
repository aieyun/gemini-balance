from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.logger import get_database_logger
import asyncio

logger = get_database_logger()


# 数据库连接重试配置
MAX_RETRIES = 5
RETRY_DELAY = 1  # 初始重试延迟（秒）

# 创建异步引擎，添加MySQL特定配置
try:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,        # 自动检测断开的连接
        pool_recycle=1800,         # 连接回收时间（30分钟）
        echo=False,                # 是否打印SQL语句
        pool_size=10,              # 连接池大小
        max_overflow=20,           # 最大溢出连接数
        pool_timeout=30,           # 从连接池获取连接的超时时间
        connect_args={
            "connect_timeout": 10, # 连接超时时间
            "charset": "utf8mb4"   # 使用utf8mb4字符集支持完整的Unicode
        }
    )
    logger.info("Database engine created successfully")
except ImportError as e:
    logger.error(f"Database driver import error: {e}")
    raise
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# 创建异步会话
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    """获取数据库会话，带有重试机制"""
    for attempt in range(MAX_RETRIES):
        try:
            async with AsyncSessionLocal() as session:
                logger.debug("Database session created")
                try:
                    yield session
                finally:
                    await session.close()
                    logger.debug("Database session closed")
            return  # 成功获取会话并使用后退出
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                # 使用指数退避策略
                retry_delay = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Database connection failed (attempt {attempt+1}/{MAX_RETRIES}): {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to get database session after {MAX_RETRIES} attempts: {e}")
                raise

# 数据库健康检查函数
async def check_db_connection() -> bool:
    """检查数据库连接是否正常"""
    try:
        async with AsyncSessionLocal() as session:
            # 执行简单查询测试连接
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
