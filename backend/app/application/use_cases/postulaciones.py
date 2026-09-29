from dataclasses import dataclass, field

from app.application.ports import AdoptanteRepository, AnimalRepository, PostulacionRepository
from app.domain.entities import Animal, EstadoAnimal, EstadoPostulacion, Postulacion
from app.domain.exceptions import PostulacionDuplicada, RecursoNoEncontrado


@dataclass
class ResultadoResolucion:
    """Lo que cambió al resolver una postulación. El adaptador de entrada lo usa para armar
    la respuesta JSON:API con el animal y las cerradas en `included`."""

    postulacion: Postulacion
    animal: Animal
    cerradas_automaticamente: list[Postulacion] = field(default_factory=list)


class _ConRepositorios:
    def __init__(self, animales: AnimalRepository, postulaciones: PostulacionRepository):
        self._animales = animales
        self._postulaciones = postulaciones

    async def _animal(self, animal_id: str) -> Animal:
        animal = await self._animales.obtener(animal_id)
        if animal is None:
            raise RecursoNoEncontrado(f"No existe el animal {animal_id}.")
        return animal

    async def _postulacion(self, postulacion_id: str) -> Postulacion:
        postulacion = await self._postulaciones.obtener(postulacion_id)
        if postulacion is None:
            raise RecursoNoEncontrado(f"No existe la postulación {postulacion_id}.")
        return postulacion


class Postular(_ConRepositorios):
    """Pasos 2-3 del flujo: el adoptante postula y el sistema valida las reglas 1 y 2."""

    def __init__(
        self,
        animales: AnimalRepository,
        postulaciones: PostulacionRepository,
        adoptantes: AdoptanteRepository,
    ):
        super().__init__(animales, postulaciones)
        self._adoptantes = adoptantes

    async def ejecutar(self, *, animal_id: str, adoptante_id: str, mensaje: str) -> Postulacion:
        animal = await self._animal(animal_id)
        if await self._adoptantes.obtener(adoptante_id) is None:
            raise RecursoNoEncontrado(f"No existe el adoptante {adoptante_id}.")
        animal.validar_postulable()  # regla 1
        if await self._postulaciones.existe_pendiente(adoptante_id, animal_id):  # regla 2
            raise PostulacionDuplicada("Ya tienes una postulación pendiente para este animal.")

        postulacion = await self._postulaciones.guardar(
            Postulacion(animal_id=animal_id, adoptante_id=adoptante_id, mensaje=mensaje)
        )
        animal.registrar_postulacion()
        await self._animales.guardar(animal)
        return postulacion


class AprobarPostulacion(_ConRepositorios):
    """Pasos 4-5: al aprobar, el animal pasa a adoptado y las demás pendientes se cierran (regla 3)."""

    async def ejecutar(self, postulacion_id: str) -> ResultadoResolucion:
        postulacion = await self._postulacion(postulacion_id)
        animal = await self._animal(postulacion.animal_id)

        postulacion.aprobar()  # falla si ya estaba resuelta
        animal.marcar_adoptado()

        pendientes = await self._postulaciones.listar_por_animal(
            animal.id, estado=EstadoPostulacion.PENDIENTE
        )
        cerradas = []
        for otra in pendientes:
            if otra.id == postulacion.id:
                continue
            otra.cerrar_automaticamente()
            cerradas.append(await self._postulaciones.guardar(otra))

        postulacion = await self._postulaciones.guardar(postulacion)
        animal = await self._animales.guardar(animal)
        return ResultadoResolucion(postulacion, animal, cerradas)


class RechazarPostulacion(_ConRepositorios):
    """El refugio rechaza una postulación; si no quedan pendientes, el animal vuelve a disponible."""

    async def ejecutar(self, postulacion_id: str) -> ResultadoResolucion:
        postulacion = await self._postulacion(postulacion_id)
        animal = await self._animal(postulacion.animal_id)

        postulacion.rechazar()
        postulacion = await self._postulaciones.guardar(postulacion)

        quedan = await self._postulaciones.listar_por_animal(
            animal.id, estado=EstadoPostulacion.PENDIENTE
        )
        if not quedan and animal.estado == EstadoAnimal.POSTULADO:
            animal.liberar()
            animal = await self._animales.guardar(animal)
        return ResultadoResolucion(postulacion, animal)


class ListarPostulaciones:
    """"Mis postulaciones" (por adoptante) y panel del refugio (por refugio)."""

    def __init__(self, postulaciones: PostulacionRepository):
        self._postulaciones = postulaciones

    async def por_adoptante(
        self, adoptante_id: str, estado: EstadoPostulacion | None = None
    ) -> list[Postulacion]:
        return _con_estado(await self._postulaciones.listar_por_adoptante(adoptante_id), estado)

    async def por_refugio(
        self, refugio_id: str, estado: EstadoPostulacion | None = None
    ) -> list[Postulacion]:
        return _con_estado(await self._postulaciones.listar_por_refugio(refugio_id), estado)


def _con_estado(postulaciones: list[Postulacion], estado: EstadoPostulacion | None) -> list[Postulacion]:
    return [p for p in postulaciones if estado is None or p.estado == estado]
