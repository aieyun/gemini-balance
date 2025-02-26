import asyncio
from app.database import engine, Base
from app.models.api_key import APIKey
from app.core.config import settings

async def init_db():
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        
        # 初始化API keys
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # 检查是否已有数据
            result = await session.execute(select(APIKey))
            existing_keys = result.scalars().all()
            
            if not existing_keys:
                # 插入初始API keys
                for key in settings.API_KEYS:
                    new_key = APIKey(key=key)
                    session.add(new_key)
                
                await session.commit()

if __name__ == "__main__":
    asyncio.run(init_db()) 