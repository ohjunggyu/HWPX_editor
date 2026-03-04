import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "HWPX Editor API"
    API_V1_STR: str = "/api/v1"
    TEMP_DIR: str = os.path.join(os.getcwd(), "tmp_hwpx")

    class Config:
        case_sensitive = True


settings = Settings()

os.makedirs(settings.TEMP_DIR, exist_ok=True)
