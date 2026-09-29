"""Cableado: qué adaptador de salida concreto reciben los casos de uso. Es el único lugar que
conoce las implementaciones; los routers piden `Repositorios` con Depends() y nada más.

Por ahora se inyecta el adaptador in-memory. Para usar MongoDB basta con cambiar
`crear_repositorios()`; ni los routers ni los casos de uso se enteran.
"""
from dataclasses import dataclass
from functools import lru_cache

from app.adapters.outbound.persistence.memory import (
    InMemoryAdoptanteRepository,
    InMemoryAnimalRepository,
    InMemoryPostulacionRepository,
    InMemoryRefugioRepository,
)
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


@lru_cache
def get_repositorios() -> Repositorios:
    """Una sola instancia por proceso (los datos en memoria se comparten entre peticiones).
    Las pruebas la reemplazan con app.dependency_overrides."""
    return crear_repositorios_en_memoria()
