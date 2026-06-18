from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "双标注质检抽样平台"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./biaozhu.db"

    class Config:
        env_file = ".env"


settings = Settings()
