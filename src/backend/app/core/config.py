from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str

    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = False

    NLP_MODEL_PATH: str = ""
    MATCHER_MODEL_PATH: str = ""

    SCHEDULER_TIMEOUT_SECONDS: int = 12
    SCHEDULER_MAX_DISPLACEMENT_LAYERS: int = 1


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
