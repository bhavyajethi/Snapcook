from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    project_name: str = "SnapCook"
    redis_url: str 
    gemini_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
