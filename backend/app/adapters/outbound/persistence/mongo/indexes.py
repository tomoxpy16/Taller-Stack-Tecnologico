from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel

# Índices del adaptador de persistencia. create_indexes es idempotente: se aplica en cada
# arranque del backend, también sobre volúmenes existentes y sobre bases de prueba nuevas.
INDEXES: dict[str, list[IndexModel]] = {
    "animales": [
        IndexModel([("estado", ASCENDING)]),
        IndexModel([("refugio_id", ASCENDING)]),
    ],
    "postulaciones": [
        IndexModel([("animal_id", ASCENDING), ("estado", ASCENDING)]),
        # Respaldo en persistencia de la regla de negocio: un adoptante no puede tener
        # más de una postulación pendiente sobre el mismo animal.
        IndexModel(
            [("adoptante_id", ASCENDING), ("animal_id", ASCENDING)],
            unique=True,
            partialFilterExpression={"estado": "pendiente"},
            name="postulacion_pendiente_unica",
        ),
    ],
    "adoptantes": [
        IndexModel([("email", ASCENDING)], unique=True),
    ],
    "refugios": [
        IndexModel([("email", ASCENDING)], unique=True),
    ],
}


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    for collection, indexes in INDEXES.items():
        await db[collection].create_indexes(indexes)
