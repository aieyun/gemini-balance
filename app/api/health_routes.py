from fastapi import APIRouter, Request
from app.core.logger import get_health_logger
from app.database import check_db_connection
from app.services.key_manager import get_key_manager_instance
import time
import platform
import psutil

# 配置日志
logger = get_health_logger()

router = APIRouter()

@router.get("/health")
async def health_check(request: Request):
    """
    基本健康检查端点
    """
    logger.info("Basic health check endpoint called")
    return {"status": "healthy", "timestamp": time.time()}

@router.get("/health/detailed")
async def detailed_health_check(request: Request):
    """
    详细健康检查端点，包括系统信息
    """
    logger.info("Detailed health check endpoint called")
    
    # 获取系统信息
    system_info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": platform.python_version(),
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
    }
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "system_info": system_info
    }

@router.get("/health/db")
async def db_health_check():
    """
    数据库健康检查端点
    """
    logger.info("Database health check endpoint called")
    
    start_time = time.time()
    db_status = await check_db_connection()
    response_time = time.time() - start_time
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database_connection": "ok" if db_status else "failed",
        "response_time_ms": round(response_time * 1000, 2),
        "timestamp": time.time()
    }

@router.get("/health/keys")
async def keys_health_check():
    """
    API密钥健康检查端点
    """
    logger.info("Keys health check endpoint called")
    
    try:
        key_manager = await get_key_manager_instance()
        keys_status = await key_manager.get_keys_by_status()
        
        valid_count = len(keys_status["valid_keys"])
        invalid_count = len(keys_status["invalid_keys"])
        total_count = valid_count + invalid_count
        
        return {
            "status": "healthy" if valid_count > 0 else "warning",
            "keys_status": {
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "total_count": total_count,
                "valid_percentage": round((valid_count / total_count) * 100, 2) if total_count > 0 else 0
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Keys health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }
