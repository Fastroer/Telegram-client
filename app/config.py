from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_id: int
    api_hash: str
    db_url: str

    class Config:
        env_file = ".env"

settings = Settings()
