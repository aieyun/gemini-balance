import uvicorn
from app.core.app import create_application
from app.api import gemini_routes, openai_routes, auth_routes, health_routes
from app.core.logger import get_main_logger

# 创建应用
app = create_application()

logger = get_main_logger()

# 包含所有路由
app.include_router(auth_routes.router)
app.include_router(health_routes.router)
app.include_router(openai_routes.router)
app.include_router(gemini_routes.router)
app.include_router(gemini_routes.router_v1beta)

if __name__ == "__main__":
    logger.info("Starting application server...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
