from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.logger import get_app_logger
from app.services.key_manager import get_key_manager_instance
from app.core.config import settings
from app.middleware.auth_middleware import auth_middleware

# 配置日志
logger = get_app_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件代码
    logger.info("Application starting up...")
    try:
        # 初始化 KeyManager 并存储在应用状态中
        app.state.key_manager = await get_key_manager_instance(settings.API_KEYS)
        logger.info("KeyManager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize KeyManager: {str(e)}")
        raise
    
    yield  # 这里会在应用运行期间暂停
    
    # 关闭事件代码（如果有的话）
    logger.info("Application shutting down...")
    # 这里可以添加清理资源的代码

def create_application() -> FastAPI:
    """
    创建并配置FastAPI应用
    """
    app = FastAPI(lifespan=lifespan)
    
    # 配置Jinja2模板
    templates = Jinja2Templates(directory="app/templates")
    app.state.templates = templates
    
    # 配置静态文件
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # 添加中间件来处理未经身份验证的请求
    app.middleware("http")(auth_middleware)
    
    # 配置CORS中间件
    # 从环境变量获取允许的源，如果未设置则使用默认值
    allowed_origins = settings.CORS_ALLOWED_ORIGINS or ["*"]
    
    # 在生产环境中，建议使用具体的域名列表而不是通配符
    if "*" in allowed_origins and settings.ENV != "development":
        logger.warning("Using wildcard CORS origin in non-development environment is not recommended")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization", 
            "Content-Type", 
            "Accept", 
            "Origin", 
            "User-Agent",
            "DNT",
            "Cache-Control", 
            "X-Requested-With",
            "X-Goog-Api-Key"
        ],
        expose_headers=[
            "Content-Length", 
            "Content-Type",
            "X-Request-ID"
        ],
        max_age=3600,  # 预检请求缓存时间增加到1小时
    )
    
    return app
