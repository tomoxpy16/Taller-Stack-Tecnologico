from app.application.ports import AdoptanteRepository
from app.domain.entities import Adoptante
from app.domain.exceptions import RecursoNoEncontrado


class RegistrarAdoptante:
    """Registro mínimo sin login (contrato API, sección 5.3): si el email ya existe, se reutiliza
    ese adoptante en lugar de crear un duplicado."""

    def __init__(self, adoptantes: AdoptanteRepository):
        self._adoptantes = adoptantes

    async def ejecutar(self, adoptante: Adoptante) -> tuple[Adoptante, bool]:
        """Devuelve el adoptante y si fue creado (True) o ya existía (False)."""
        existente = await self._adoptantes.obtener_por_email(adoptante.email)
        if existente is not None:
            return existente, False
        return await self._adoptantes.guardar(adoptante.model_copy(update={"id": None})), True


class ConsultarAdoptante:
    def __init__(self, adoptantes: AdoptanteRepository):
        self._adoptantes = adoptantes

    async def ejecutar(self, adoptante_id: str) -> Adoptante:
        adoptante = await self._adoptantes.obtener(adoptante_id)
        if adoptante is None:
            raise RecursoNoEncontrado(f"No existe el adoptante {adoptante_id}.")
        return adoptante
