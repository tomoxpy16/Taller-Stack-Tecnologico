"""Adaptador de salida en memoria: cumple los mismos puertos que el de Mongo, guardando las
entidades en diccionarios. Sirve para probar los casos de uso sin levantar una base de datos.

Guarda y devuelve copias: así, igual que con una base real, modificar una entidad no cambia lo
persistido hasta llamar a guardar(). Si devolviera la misma instancia, ocultaría ese tipo de bugs.
"""
from typing import Callable, Generic, TypeVar
from uuid import uuid4

from app.domain.entities import (
    Adoptante,
    Animal,
    Entidad,
    Especie,
    EstadoAnimal,
    EstadoPostulacion,
    Postulacion,
    Refugio,
)

E = TypeVar("E", bound=Entidad)


class _Almacen(Generic[E]):
    def __init__(self, iniciales: list[E] | None = None):
        self._datos: dict[str, E] = {}
        for entidad in iniciales or []:
            self._guardar_copia(entidad)

    def _guardar_copia(self, entidad: E) -> E:
        copia = entidad.model_copy(deep=True)
        if copia.id is None:
            copia.id = uuid4().hex
        self._datos[copia.id] = copia
        return copia.model_copy(deep=True)

    def _obtener_copia(self, entidad_id: str) -> E | None:
        entidad = self._datos.get(entidad_id)
        return entidad.model_copy(deep=True) if entidad else None

    def _filtrar(self, condicion: Callable[[E], bool], orden: Callable[[E], object]) -> list[E]:
        encontradas = sorted((e for e in self._datos.values() if condicion(e)), key=orden, reverse=True)
        return [e.model_copy(deep=True) for e in encontradas]


class InMemoryAnimalRepository(_Almacen[Animal]):
    async def obtener(self, animal_id: str) -> Animal | None:
        return self._obtener_copia(animal_id)

    async def listar(
        self,
        *,
        estado: EstadoAnimal | None = None,
        especie: Especie | None = None,
        refugio_id: str | None = None,
        pagina: int = 1,
        tamano: int = 12,
    ) -> tuple[list[Animal], int]:
        encontrados = self._filtrar(
            lambda a: (estado is None or a.estado == estado)
            and (especie is None or a.especie == especie)
            and (refugio_id is None or a.refugio_id == refugio_id),
            orden=lambda a: a.fecha_publicacion,
        )
        inicio = (pagina - 1) * tamano
        return encontrados[inicio:inicio + tamano], len(encontrados)

    async def guardar(self, animal: Animal) -> Animal:
        return self._guardar_copia(animal)

    def ids_del_refugio(self, refugio_id: str) -> set[str]:
        return {a.id for a in self._datos.values() if a.refugio_id == refugio_id}


class InMemoryPostulacionRepository(_Almacen[Postulacion]):
    def __init__(self, animales: InMemoryAnimalRepository, iniciales: list[Postulacion] | None = None):
        # Necesita los animales para filtrar por refugio, como haría un $lookup en Mongo.
        self._animales = animales
        super().__init__(iniciales)

    def _listar(self, condicion: Callable[[Postulacion], bool]) -> list[Postulacion]:
        return self._filtrar(condicion, orden=lambda p: p.fecha_postulacion)

    async def obtener(self, postulacion_id: str) -> Postulacion | None:
        return self._obtener_copia(postulacion_id)

    async def listar_por_animal(
        self, animal_id: str, *, estado: EstadoPostulacion | None = None
    ) -> list[Postulacion]:
        return self._listar(lambda p: p.animal_id == animal_id and (estado is None or p.estado == estado))

    async def listar_por_adoptante(self, adoptante_id: str) -> list[Postulacion]:
        return self._listar(lambda p: p.adoptante_id == adoptante_id)

    async def listar_por_refugio(self, refugio_id: str) -> list[Postulacion]:
        del_refugio = self._animales.ids_del_refugio(refugio_id)
        return self._listar(lambda p: p.animal_id in del_refugio)

    async def existe_pendiente(self, adoptante_id: str, animal_id: str) -> bool:
        return any(
            p.adoptante_id == adoptante_id and p.animal_id == animal_id and p.esta_pendiente
            for p in self._datos.values()
        )

    async def guardar(self, postulacion: Postulacion) -> Postulacion:
        return self._guardar_copia(postulacion)


class InMemoryRefugioRepository(_Almacen[Refugio]):
    async def obtener(self, refugio_id: str) -> Refugio | None:
        return self._obtener_copia(refugio_id)

    async def listar(self) -> list[Refugio]:
        return sorted(
            (r.model_copy(deep=True) for r in self._datos.values()), key=lambda r: r.nombre
        )


class InMemoryAdoptanteRepository(_Almacen[Adoptante]):
    async def obtener(self, adoptante_id: str) -> Adoptante | None:
        return self._obtener_copia(adoptante_id)

    async def obtener_por_email(self, email: str) -> Adoptante | None:
        for adoptante in self._datos.values():
            if adoptante.email.lower() == email.lower():
                return adoptante.model_copy(deep=True)
        return None

    async def guardar(self, adoptante: Adoptante) -> Adoptante:
        return self._guardar_copia(adoptante)
