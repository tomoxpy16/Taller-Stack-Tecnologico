from app.application.ports import RefugioRepository
from app.domain.entities import Refugio
from app.domain.exceptions import RecursoNoEncontrado


class ListarRefugios:
    def __init__(self, refugios: RefugioRepository):
        self._refugios = refugios

    async def ejecutar(self) -> list[Refugio]:
        return await self._refugios.listar()


class ConsultarRefugio:
    def __init__(self, refugios: RefugioRepository):
        self._refugios = refugios

    async def ejecutar(self, refugio_id: str) -> Refugio:
        refugio = await self._refugios.obtener(refugio_id)
        if refugio is None:
            raise RecursoNoEncontrado(f"No existe el refugio {refugio_id}.")
        return refugio
