from fastapi import Request
from fastapi.responses import RedirectResponse
from app.core.security import verify_auth_token
from app.core.logger import get_auth_middleware_logger

# 配置日志
logger = get_auth_middleware_logger()

async def auth_middleware(request: Request, call_next):
    """
    认证中间件，用于处理未经身份验证的请求
    """
    # 允许特定路径绕过身份验证
    if (request.url.path not in ["/", "/auth"] and 
        not request.url.path.startswith("/static") and
        not request.url.path.startswith("/gemini") and
        not request.url.path.startswith("/v1") and
        not request.url.path.startswith("/v1beta") and
        not request.url.path.startswith("/health") and
        not request.url.path.startswith("/hf")):
        auth_token = request.cookies.get("auth_token")
        if not auth_token or not verify_auth_token(auth_token):
            logger.warning(f"Unauthorized access attempt to {request.url.path}")
            return RedirectResponse(url="/")
        logger.debug("Request authenticated successfully")
    response = await call_next(request)
    return response
