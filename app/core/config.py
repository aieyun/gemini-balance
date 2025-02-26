from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    API_KEYS: List[str]
    ALLOWED_TOKENS: List[str]
    BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    MODEL_SEARCH: List[str] = ["gemini-2.0-flash-exp"]
    TOOLS_CODE_EXECUTION_ENABLED: bool = False
    SHOW_SEARCH_LINK: bool = True
    SHOW_THINKING_PROCESS: bool = True
    AUTH_TOKEN: str = ""
    MAX_FAILURES: int = 3
    PAID_KEY: str = ""
    CREATE_IMAGE_MODEL: str = "imagen-3.0-generate-002"
    UPLOAD_PROVIDER: str = "smms"
    SMMS_SECRET_TOKEN: str = ""
    TEST_MODEL: str = "gemini-1.5-flash"
    
    # MySQL数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "user"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "gemini"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    def __init__(self):
        super().__init__()
        if not self.AUTH_TOKEN:
            self.AUTH_TOKEN = self.ALLOWED_TOKENS[0] if self.ALLOWED_TOKENS else ""

    class Config:
        env_file = ".env"


settings = Settings()
