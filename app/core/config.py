from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # 环境配置
    ENV: str = os.environ.get("ENV", "development")  # 环境: development, production, testing
    DEBUG: bool = ENV == "development"
    
    # API密钥配置
    API_KEYS: List[str]
    ALLOWED_TOKENS: List[str]
    AUTH_TOKEN: str = ""
    MAX_FAILURES: int = 3
    PAID_KEY: str = ""
    
    # API服务配置
    BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    MODEL_SEARCH: List[str] = ["gemini-2.0-flash-exp"]
    TOOLS_CODE_EXECUTION_ENABLED: bool = False
    SHOW_SEARCH_LINK: bool = True
    SHOW_THINKING_PROCESS: bool = True
    TEST_MODEL: str = "gemini-1.5-flash"
    
    # 图像生成配置
    CREATE_IMAGE_MODEL: str = "imagen-3.0-generate-002"
    UPLOAD_PROVIDER: str = "smms"
    SMMS_SECRET_TOKEN: str = ""
    
    # CORS配置
    CORS_ALLOWED_ORIGINS: Optional[List[str]] = None
    
    # 性能配置
    REQUEST_TIMEOUT: int = 300  # 请求超时时间（秒）
    MAX_RETRIES: int = 3        # 最大重试次数
    
    # MySQL数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "user"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "gemini"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    def __init__(self):
        super().__init__()
        if not self.AUTH_TOKEN and self.ALLOWED_TOKENS:
            self.AUTH_TOKEN = self.ALLOWED_TOKENS[0]
        
        # 根据环境设置默认值
        if self.ENV == "production":
            if not self.CORS_ALLOWED_ORIGINS:
                self.CORS_ALLOWED_ORIGINS = []  # 生产环境默认不允许任何跨域请求，需要明确配置
            if self.LOG_LEVEL == "INFO":
                self.LOG_LEVEL = "WARNING"  # 生产环境默认日志级别为WARNING
        elif self.ENV == "development":
            if not self.CORS_ALLOWED_ORIGINS:
                self.CORS_ALLOWED_ORIGINS = ["*"]  # 开发环境允许所有跨域请求

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
