from app.application.ports import AnimalRepository, RefugioRepository
from app.domain.entities import Animal, Especie, EstadoAnimal
from app.domain.exceptions import RecursoNoEncontrado

TAMANO_PAGINA_MAX = 50


class PublicarAnimal:
    """Paso 1 del flujo: el refugio publica un animal, que siempre entra como disponible."""

    def __init__(self, animales: AnimalRepository, refugios: RefugioRepository):
        self._animales = animales
        self._refugios = refugios

    async def ejecutar(self, animal: Animal) -> Animal:
        if await self._refugios.obtener(animal.refugio_id) is None:
            raise RecursoNoEncontrado(f"No existe el refugio {animal.refugio_id}.")
        # El estado lo gobierna el dominio: se ignora lo que venga del cliente.
        publicado = animal.model_copy(update={"id": None, "estado": EstadoAnimal.DISPONIBLE})
        return await self._animales.guardar(publicado)


class ConsultarAnimal:
    def __init__(self, animales: AnimalRepository):
        self._animales = animales

    async def ejecutar(self, animal_id: str) -> Animal:
        animal = await self._animales.obtener(animal_id)
        if animal is None:
            raise RecursoNoEncontrado(f"No existe el animal {animal_id}.")
        return animal


class ListarAnimales:
    def __init__(self, animales: AnimalRepository):
        self._animales = animales

    async def ejecutar(
        self,
        *,
        estado: EstadoAnimal | None = None,
        especie: Especie | None = None,
        refugio_id: str | None = None,
        pagina: int = 1,
        tamano: int = 12,
    ) -> tuple[list[Animal], int]:
        return await self._animales.listar(
            estado=estado,
            especie=especie,
            refugio_id=refugio_id,
            pagina=max(pagina, 1),
            tamano=min(max(tamano, 1), TAMANO_PAGINA_MAX),
        )
