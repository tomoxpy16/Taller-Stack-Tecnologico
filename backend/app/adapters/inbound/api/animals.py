from fastapi import APIRouter, Depends, Query, Request

from app.adapters.inbound.api import jsonapi
from app.adapters.inbound.api.dependencies import Repositorios, get_repositorios
from app.adapters.inbound.api.schemas import AnimalCrear
from app.application.use_cases import ConsultarAnimal, ListarAnimales, PublicarAnimal
from app.application.use_cases.animales import TAMANO_PAGINA_MAX
from app.domain.entities import Animal, Especie, EstadoAnimal

router = APIRouter(prefix="/animals", tags=["animals"], default_response_class=jsonapi.JSONAPIResponse)

INCLUDES = {"refugio"}


async def _refugios_de(animales: list[Animal], repos: Repositorios) -> list[dict]:
    incluidos = []
    for refugio_id in dict.fromkeys(a.refugio_id for a in animales):
        refugio = await repos.refugios.obtener(refugio_id)
        if refugio is not None:
            incluidos.append(jsonapi.refugio(refugio))
    return incluidos


@router.get("")
async def listar_animales(
    request: Request,
    estado: EstadoAnimal | None = Query(None, alias="filter[estado]"),
    especie: Especie | None = Query(None, alias="filter[especie]"),
    refugio: str | None = Query(None, alias="filter[refugio]"),
    pagina: int = Query(1, alias="page[number]", ge=1),
    tamano: int = Query(12, alias="page[size]", ge=1, le=TAMANO_PAGINA_MAX),
    include: str | None = None,
    repos: Repositorios = Depends(get_repositorios),
):
    incluir = jsonapi.parse_include(include, INCLUDES)
    animales, total = await ListarAnimales(repos.animales).ejecutar(
        estado=estado, especie=especie, refugio_id=refugio, pagina=pagina, tamano=tamano
    )
    return jsonapi.documento(
        [jsonapi.animal(a) for a in animales],
        included=await _refugios_de(animales, repos) if "refugio" in incluir else None,
        meta={"total": total},
        links=jsonapi.links_paginacion(request, pagina, tamano, total),
    )


@router.get("/{animal_id}")
async def consultar_animal(
    animal_id: str,
    include: str | None = None,
    repos: Repositorios = Depends(get_repositorios),
):
    incluir = jsonapi.parse_include(include, INCLUDES)
    animal = await ConsultarAnimal(repos.animales).ejecutar(animal_id)
    return jsonapi.documento(
        jsonapi.animal(animal),
        included=await _refugios_de([animal], repos) if "refugio" in incluir else None,
    )


@router.post("", status_code=201, dependencies=[Depends(jsonapi.requiere_media_type)])
async def publicar_animal(cuerpo: AnimalCrear, repos: Repositorios = Depends(get_repositorios)):
    animal = await PublicarAnimal(repos.animales, repos.refugios).ejecutar(cuerpo.a_entidad())
    return jsonapi.JSONAPIResponse(
        status_code=201,
        content=jsonapi.documento(jsonapi.animal(animal), included=await _refugios_de([animal], repos)),
        headers={"Location": f"/v1/animals/{animal.id}"},
    )
