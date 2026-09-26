from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
    mongo_db_name: str = "adopciones"


settings = Settings()
