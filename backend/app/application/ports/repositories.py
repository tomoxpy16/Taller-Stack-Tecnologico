"""Puertos de salida: lo que los casos de uso necesitan de la persistencia, sin decir cómo.

Son typing.Protocol (tipado estructural): un adaptador los cumple con solo tener estos métodos,
sin heredar de nada. Los implementan el adaptador de Mongo (producción) y el in-memory (pruebas);
FastAPI inyecta el concreto con Depends(). Son async porque el adaptador real usa Motor.
"""
from typing import Protocol, runtime_checkable

from app.domain.entities import Animal, Especie, EstadoAnimal, EstadoPostulacion, Postulacion


@runtime_checkable
class AnimalRepository(Protocol):
    async def obtener(self, animal_id: str) -> Animal | None:
        """Devuelve el animal o None si no existe."""
        ...

    async def listar(
        self,
        *,
        estado: EstadoAnimal | None = None,
        especie: Especie | None = None,
        refugio_id: str | None = None,
        pagina: int = 1,
        tamano: int = 12,
    ) -> tuple[list[Animal], int]:
        """Página de animales que cumplen los filtros y el total sin paginar (meta.total)."""
        ...

    async def guardar(self, animal: Animal) -> Animal:
        """Inserta si animal.id es None (y devuelve la entidad con id asignado); si no, actualiza."""
        ...


@runtime_checkable
class PostulacionRepository(Protocol):
    async def obtener(self, postulacion_id: str) -> Postulacion | None:
        ...

    async def listar_por_animal(
        self, animal_id: str, *, estado: EstadoPostulacion | None = None
    ) -> list[Postulacion]:
        """Con estado=PENDIENTE da las que se cierran automáticamente al aprobar (regla 3)."""
        ...

    async def listar_por_adoptante(self, adoptante_id: str) -> list[Postulacion]:
        """Pantalla "Mis postulaciones"."""
        ...

    async def listar_por_refugio(self, refugio_id: str) -> list[Postulacion]:
        """Postulaciones a los animales del refugio (panel del refugio)."""
        ...

    async def existe_pendiente(self, adoptante_id: str, animal_id: str) -> bool:
        """Regla 2: ¿el adoptante ya tiene una postulación pendiente sobre este animal?"""
        ...

    async def guardar(self, postulacion: Postulacion) -> Postulacion:
        """Inserta si postulacion.id es None; si no, actualiza."""
        ...
