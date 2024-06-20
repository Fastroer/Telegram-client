from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_id: str
    api_hash: str
    db_url: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    test_postgres_user: str
    test_postgres_password: str
    test_postgres_db: str

    class ConfigDict:
        env_file = ".env"

settings = Settings()
