import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

pytestmark = pytest.mark.integration


async def test_ensure_indexes_es_idempotente(mongo_db):
    from app.adapters.outbound.persistence.mongo.indexes import ensure_indexes

    await ensure_indexes(mongo_db)
    nombres = [i["name"] async for i in mongo_db.postulaciones.list_indexes()]
    assert "postulacion_pendiente_unica" in nombres


async def test_rechaza_segunda_postulacion_pendiente_al_mismo_animal(mongo_db):
    adoptante, animal = ObjectId(), ObjectId()
    await mongo_db.postulaciones.insert_one(
        {"adoptante_id": adoptante, "animal_id": animal, "estado": "pendiente"}
    )
    with pytest.raises(DuplicateKeyError):
        await mongo_db.postulaciones.insert_one(
            {"adoptante_id": adoptante, "animal_id": animal, "estado": "pendiente"}
        )


async def test_permite_nueva_postulacion_si_la_anterior_fue_rechazada(mongo_db):
    adoptante, animal = ObjectId(), ObjectId()
    await mongo_db.postulaciones.insert_one(
        {"adoptante_id": adoptante, "animal_id": animal, "estado": "rechazada"}
    )
    await mongo_db.postulaciones.insert_one(
        {"adoptante_id": adoptante, "animal_id": animal, "estado": "pendiente"}
    )
    assert await mongo_db.postulaciones.count_documents({"animal_id": animal}) == 2


async def test_otro_adoptante_puede_postular_al_mismo_animal(mongo_db):
    animal = ObjectId()
    await mongo_db.postulaciones.insert_many([
        {"adoptante_id": ObjectId(), "animal_id": animal, "estado": "pendiente"},
        {"adoptante_id": ObjectId(), "animal_id": animal, "estado": "pendiente"},
    ])
    assert await mongo_db.postulaciones.count_documents({"animal_id": animal}) == 2


async def test_email_de_adoptante_unico(mongo_db):
    await mongo_db.adoptantes.insert_one({"nombre": "Ana", "email": "ana@mail.com"})
    with pytest.raises(DuplicateKeyError):
        await mongo_db.adoptantes.insert_one({"nombre": "Otra Ana", "email": "ana@mail.com"})
