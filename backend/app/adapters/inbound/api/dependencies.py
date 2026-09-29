"""Cableado: qué adaptador de salida concreto reciben los casos de uso. Es el único lugar que
conoce las implementaciones; los routers piden `Repositorios` con Depends() y nada más.

En producción se inyecta el adaptador de MongoDB; las pruebas HTTP lo reemplazan por el
in-memory con app.dependency_overrides. Ni los routers ni los casos de uso se enteran del cambio.
"""
from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.adapters.outbound.persistence.memory import (
    InMemoryAdoptanteRepository,
    InMemoryAnimalRepository,
    InMemoryPostulacionRepository,
    InMemoryRefugioRepository,
)
from app.adapters.outbound.persistence.mongo import (
    MongoAdoptanteRepository,
    MongoAnimalRepository,
    MongoPostulacionRepository,
    MongoRefugioRepository,
)
from app.adapters.outbound.persistence.mongo import client as mongo
from app.application.ports import (
    AdoptanteRepository,
    AnimalRepository,
    PostulacionRepository,
    RefugioRepository,
)


@dataclass(frozen=True)
class Repositorios:
    animales: AnimalRepository
    postulaciones: PostulacionRepository
    refugios: RefugioRepository
    adoptantes: AdoptanteRepository


def crear_repositorios_en_memoria() -> Repositorios:
    animales = InMemoryAnimalRepository()
    return Repositorios(
        animales=animales,
        postulaciones=InMemoryPostulacionRepository(animales),
        refugios=InMemoryRefugioRepository(),
        adoptantes=InMemoryAdoptanteRepository(),
    )


def crear_repositorios_mongo(db: AsyncIOMotorDatabase) -> Repositorios:
    animales = MongoAnimalRepository(db)
    return Repositorios(
        animales=animales,
        postulaciones=MongoPostulacionRepository(db, animales),
        refugios=MongoRefugioRepository(db),
        adoptantes=MongoAdoptanteRepository(db),
    )


def get_repositorios() -> Repositorios:
    """Repositorios de MongoDB sobre el cliente que abre el lifespan de main.py. Son objetos
    livianos sin estado propio, así que se crean por petición. Las pruebas la reemplazan con
    app.dependency_overrides."""
    return crear_repositorios_mongo(mongo.get_database())
