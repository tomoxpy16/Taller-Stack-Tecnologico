"""Adaptador de salida en memoria: cumple los mismos puertos que el de Mongo, guardando las
entidades en diccionarios. Sirve para probar los casos de uso sin levantar una base de datos.

Guarda y devuelve copias: así, igual que con una base real, modificar una entidad no cambia lo
persistido hasta llamar a guardar(). Si devolviera la misma instancia, ocultaría ese tipo de bugs.
"""
from uuid import uuid4

from app.domain.entities import Animal, Especie, EstadoAnimal, EstadoPostulacion, Postulacion


def _nuevo_id() -> str:
    return uuid4().hex


class InMemoryAnimalRepository:
    def __init__(self, iniciales: list[Animal] | None = None):
        self._datos: dict[str, Animal] = {}
        for animal in iniciales or []:
            self._guardar_copia(animal)

    def _guardar_copia(self, animal: Animal) -> Animal:
        copia = animal.model_copy(deep=True)
        if copia.id is None:
            copia.id = _nuevo_id()
        self._datos[copia.id] = copia
        return copia.model_copy(deep=True)

    async def obtener(self, animal_id: str) -> Animal | None:
        animal = self._datos.get(animal_id)
        return animal.model_copy(deep=True) if animal else None

    async def listar(
        self,
        *,
        estado: EstadoAnimal | None = None,
        especie: Especie | None = None,
        refugio_id: str | None = None,
        pagina: int = 1,
        tamano: int = 12,
    ) -> tuple[list[Animal], int]:
        encontrados = [
            a for a in self._datos.values()
            if (estado is None or a.estado == estado)
            and (especie is None or a.especie == especie)
            and (refugio_id is None or a.refugio_id == refugio_id)
        ]
        encontrados.sort(key=lambda a: a.fecha_publicacion, reverse=True)
        inicio = (pagina - 1) * tamano
        pagina_actual = encontrados[inicio:inicio + tamano]
        return [a.model_copy(deep=True) for a in pagina_actual], len(encontrados)

    async def guardar(self, animal: Animal) -> Animal:
        return self._guardar_copia(animal)


class InMemoryPostulacionRepository:
    def __init__(self, animales: InMemoryAnimalRepository, iniciales: list[Postulacion] | None = None):
        # Necesita los animales para filtrar por refugio, como haría un $lookup en Mongo.
        self._animales = animales
        self._datos: dict[str, Postulacion] = {}
        for postulacion in iniciales or []:
            self._guardar_copia(postulacion)

    def _guardar_copia(self, postulacion: Postulacion) -> Postulacion:
        copia = postulacion.model_copy(deep=True)
        if copia.id is None:
            copia.id = _nuevo_id()
        self._datos[copia.id] = copia
        return copia.model_copy(deep=True)

    def _filtrar(self, condicion) -> list[Postulacion]:
        encontradas = sorted(
            (p for p in self._datos.values() if condicion(p)),
            key=lambda p: p.fecha_postulacion,
            reverse=True,
        )
        return [p.model_copy(deep=True) for p in encontradas]

    async def obtener(self, postulacion_id: str) -> Postulacion | None:
        postulacion = self._datos.get(postulacion_id)
        return postulacion.model_copy(deep=True) if postulacion else None

    async def listar_por_animal(
        self, animal_id: str, *, estado: EstadoPostulacion | None = None
    ) -> list[Postulacion]:
        return self._filtrar(
            lambda p: p.animal_id == animal_id and (estado is None or p.estado == estado)
        )

    async def listar_por_adoptante(self, adoptante_id: str) -> list[Postulacion]:
        return self._filtrar(lambda p: p.adoptante_id == adoptante_id)

    async def listar_por_refugio(self, refugio_id: str) -> list[Postulacion]:
        del_refugio = {a.id for a in self._animales._datos.values() if a.refugio_id == refugio_id}
        return self._filtrar(lambda p: p.animal_id in del_refugio)

    async def existe_pendiente(self, adoptante_id: str, animal_id: str) -> bool:
        return any(
            p.adoptante_id == adoptante_id and p.animal_id == animal_id and p.esta_pendiente
            for p in self._datos.values()
        )

    async def guardar(self, postulacion: Postulacion) -> Postulacion:
        return self._guardar_copia(postulacion)
