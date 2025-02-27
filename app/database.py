from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

# 创建异步引擎，添加MySQL特定配置
try:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # 自动检测断开的连接
        pool_recycle=3600,   # 连接回收时间
        echo=False,          # 是否打印SQL语句
        pool_size=5,         # 连接池大小
        max_overflow=10      # 最大溢出连接数
    )
except ImportError as e:
    logging.error(f"数据库驱动程序导入错误: {e}.")
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
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 