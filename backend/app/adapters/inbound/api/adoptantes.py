from fastapi import APIRouter, Depends

from app.adapters.inbound.api import jsonapi
from app.adapters.inbound.api.dependencies import Repositorios, get_repositorios
from app.adapters.inbound.api.schemas import AdoptanteCrear
from app.application.use_cases import ConsultarAdoptante, RegistrarAdoptante

router = APIRouter(prefix="/adoptantes", tags=["adoptantes"], default_response_class=jsonapi.JSONAPIResponse)


@router.post("", status_code=201, dependencies=[Depends(jsonapi.requiere_media_type)])
async def registrar_adoptante(cuerpo: AdoptanteCrear, repos: Repositorios = Depends(get_repositorios)):
    """Registro mínimo sin login: si el email ya existe devuelve 200 con ese adoptante."""
    adoptante, creado = await RegistrarAdoptante(repos.adoptantes).ejecutar(cuerpo.a_entidad())
    return jsonapi.JSONAPIResponse(
        status_code=201 if creado else 200,
        content=jsonapi.documento(jsonapi.adoptante(adoptante)),
        headers={"Location": f"/v1/adoptantes/{adoptante.id}"} if creado else None,
    )


@router.get("/{adoptante_id}")
async def consultar_adoptante(adoptante_id: str, repos: Repositorios = Depends(get_repositorios)):
    adoptante = await ConsultarAdoptante(repos.adoptantes).ejecutar(adoptante_id)
    return jsonapi.documento(jsonapi.adoptante(adoptante))
