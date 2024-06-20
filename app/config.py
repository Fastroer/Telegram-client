from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_id: str
    api_hash: str

    class ConfigDict:
        env_file = ".env"

settings = Settings()
