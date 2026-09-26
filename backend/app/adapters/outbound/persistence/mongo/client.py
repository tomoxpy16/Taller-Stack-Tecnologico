from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None


def connect() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)


def close() -> None:
    if _client is not None:
        _client.close()


def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Cliente de Mongo no inicializado")
    return _client[settings.mongo_db_name]
