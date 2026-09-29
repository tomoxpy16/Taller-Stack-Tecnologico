from fastapi import APIRouter, Depends, Query

from app.adapters.inbound.api import jsonapi
from app.adapters.inbound.api.dependencies import Repositorios, get_repositorios
from app.adapters.inbound.api.schemas import PostulacionCrear, PostulacionResolver
from app.application.use_cases import (
    AprobarPostulacion,
    ListarPostulaciones,
    Postular,
    RechazarPostulacion,
)
from app.domain.entities import EstadoPostulacion, Postulacion

router = APIRouter(prefix="/postulaciones", tags=["postulaciones"], default_response_class=jsonapi.JSONAPIResponse)

INCLUDES = {"animal", "adoptante"}


async def _incluidos(postulaciones: list[Postulacion], incluir: set[str], repos: Repositorios) -> list[dict]:
    incluidos = []
    if "animal" in incluir:
        for animal_id in dict.fromkeys(p.animal_id for p in postulaciones):
            if (animal := await repos.animales.obtener(animal_id)) is not None:
                incluidos.append(jsonapi.animal(animal))
    if "adoptante" in incluir:
        for adoptante_id in dict.fromkeys(p.adoptante_id for p in postulaciones):
            if (adoptante := await repos.adoptantes.obtener(adoptante_id)) is not None:
                incluidos.append(jsonapi.adoptante(adoptante))
    return incluidos


@router.get("")
async def listar_postulaciones(
    refugio: str | None = Query(None, alias="filter[refugio]"),
    adoptante: str | None = Query(None, alias="filter[adoptante]"),
    estado: EstadoPostulacion | None = Query(None, alias="filter[estado]"),
    include: str | None = None,
    repos: Repositorios = Depends(get_repositorios),
):
    incluir = jsonapi.parse_include(include, INCLUDES)
    listar = ListarPostulaciones(repos.postulaciones)
    if adoptante:
        postulaciones = await listar.por_adoptante(adoptante, estado)
        if refugio:
            del_refugio = {p.id for p in await listar.por_refugio(refugio)}
            postulaciones = [p for p in postulaciones if p.id in del_refugio]
    elif refugio:
        postulaciones = await listar.por_refugio(refugio, estado)
    else:
        raise jsonapi.ErrorDeSolicitud(
            400, "SOLICITUD_MALFORMADA", "Falta un filtro",
            "Indica filter[refugio] o filter[adoptante].", {"parameter": "filter"},
        )
    return jsonapi.documento(
        [jsonapi.postulacion(p) for p in postulaciones],
        included=await _incluidos(postulaciones, incluir, repos) if incluir else None,
        meta={"total": len(postulaciones)},
    )


@router.post("", status_code=201, dependencies=[Depends(jsonapi.requiere_media_type)])
async def postular(cuerpo: PostulacionCrear, repos: Repositorios = Depends(get_repositorios)):
    datos = cuerpo.data
    postulacion = await Postular(repos.animales, repos.postulaciones, repos.adoptantes).ejecutar(
        animal_id=datos.relationships.animal.data.id,
        adoptante_id=datos.relationships.adoptante.data.id,
        mensaje=datos.attributes.mensaje,
    )
    return jsonapi.JSONAPIResponse(
        status_code=201,
        content=jsonapi.documento(
            jsonapi.postulacion(postulacion),
            included=await _incluidos([postulacion], INCLUDES, repos),
        ),
    )


@router.patch("/{postulacion_id}", dependencies=[Depends(jsonapi.requiere_media_type)])
async def resolver_postulacion(
    postulacion_id: str,
    cuerpo: PostulacionResolver,
    repos: Repositorios = Depends(get_repositorios),
):
    """Aprueba o rechaza. Devuelve en `included` el animal y las postulaciones cerradas
    automáticamente, para que el panel se actualice con una sola respuesta."""
    if cuerpo.data.id != postulacion_id:
        raise jsonapi.ErrorDeSolicitud(
            409, "ID_NO_COINCIDE", "El id no coincide",
            "data.id debe ser igual al id de la URL.", {"pointer": "/data/id"},
        )
    caso = AprobarPostulacion if cuerpo.data.attributes.estado == "aprobada" else RechazarPostulacion
    resultado = await caso(repos.animales, repos.postulaciones).ejecutar(postulacion_id)
    return jsonapi.documento(
        jsonapi.postulacion(resultado.postulacion),
        included=[jsonapi.animal(resultado.animal)]
        + [jsonapi.postulacion(p) for p in resultado.cerradas_automaticamente],
        meta={"postulacionesCerradasAutomaticamente": len(resultado.cerradas_automaticamente)},
    )
