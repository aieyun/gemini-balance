from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.security import verify_auth_token
from app.core.logger import get_auth_logger

# 配置日志
logger = get_auth_logger()

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def auth_page(request: Request):
    """
    认证页面路由
    """
    templates = request.app.state.templates
    return templates.TemplateResponse("auth.html", {"request": request})


@router.post("/auth")
async def authenticate(request: Request):
    """
    处理认证请求
    """
    try:
        form = await request.form()
        auth_token = form.get("auth_token")
        if not auth_token:
            logger.warning("Authentication attempt with empty token")
            return RedirectResponse(url="/", status_code=302)
        
        if verify_auth_token(auth_token):
            logger.info("Successful authentication")
            response = RedirectResponse(url="/keys", status_code=302)
            response.set_cookie(key="auth_token", value=auth_token, httponly=True, max_age=3600)
            return response
        logger.warning("Failed authentication attempt with invalid token")
        return RedirectResponse(url="/", status_code=302)
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return RedirectResponse(url="/", status_code=302)

@router.get("/keys", response_class=HTMLResponse)
async def keys_page(request: Request):
    """
    密钥状态页面路由
    """
    try:
        auth_token = request.cookies.get("auth_token")
        if not auth_token or not verify_auth_token(auth_token):
            logger.warning("Unauthorized access attempt to keys page")
            return RedirectResponse(url="/", status_code=302)
        
        # 从应用状态中获取 key_manager
        key_manager = request.app.state.key_manager
        if not key_manager:
            logger.error("KeyManager not initialized")
            raise RuntimeError("KeyManager not initialized")
            
        keys_status = await key_manager.get_keys_by_status()
        total = len(keys_status["valid_keys"]) + len(keys_status["invalid_keys"])
        logger.info(f"Keys status retrieved successfully. Total keys: {total}")
        
        templates = request.app.state.templates
        return templates.TemplateResponse("keys_status.html", {
            "request": request,
            "valid_keys": keys_status["valid_keys"],
            "invalid_keys": keys_status["invalid_keys"],
            "total": total
        })
    except Exception as e:
        logger.error(f"Error retrieving keys status: {str(e)}")
        raise
