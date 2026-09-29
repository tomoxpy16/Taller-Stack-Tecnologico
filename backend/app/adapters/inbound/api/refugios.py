from fastapi import APIRouter, Depends

from app.adapters.inbound.api import jsonapi
from app.adapters.inbound.api.dependencies import Repositorios, get_repositorios
from app.application.use_cases import ConsultarRefugio, ListarRefugios

router = APIRouter(prefix="/refugios", tags=["refugios"], default_response_class=jsonapi.JSONAPIResponse)


@router.get("")
async def listar_refugios(repos: Repositorios = Depends(get_repositorios)):
    refugios = await ListarRefugios(repos.refugios).ejecutar()
    return jsonapi.documento([jsonapi.refugio(r) for r in refugios], meta={"total": len(refugios)})


@router.get("/{refugio_id}")
async def consultar_refugio(refugio_id: str, repos: Repositorios = Depends(get_repositorios)):
    refugio = await ConsultarRefugio(repos.refugios).ejecutar(refugio_id)
    return jsonapi.documento(jsonapi.refugio(refugio))
