from pydantic import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PDF Job Parser"
    DEBUG: bool = True

settings = Settings()
