import os
import uuid

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from app.adapters.outbound.persistence.mongo.indexes import ensure_indexes

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin:admin123@localhost:27017/?authSource=admin",
)


@pytest.fixture
async def mongo_db():
    """Base de datos Mongo desechable: única por prueba y eliminada al terminar."""
    client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    try:
        await client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB no disponible (levantarlo con: docker compose up -d mongodb)")

    name = f"adopciones_test_{uuid.uuid4().hex[:8]}"
    db = client[name]
    await ensure_indexes(db)
    yield db
    await client.drop_database(name)
    client.close()
