from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://pantry:pantry@localhost:5432/pantry"
    app_version: str = "dev"

settings = Settings()
