"""Traduce excepciones a documentos de error JSON:API (contrato, sección 4).

Aquí vive el único mapeo excepción de dominio -> código HTTP: el dominio no conoce HTTP (ADR-006).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from pydantic.alias_generators import to_camel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.inbound.api.jsonapi import ErrorDeSolicitud, JSONAPIResponse
from app.domain.exceptions import (
    AnimalNoDisponible,
    ErrorDeDominio,
    PostulacionDuplicada,
    PostulacionYaResuelta,
    RecursoNoEncontrado,
    TransicionInvalida,
)

log = logging.getLogger(__name__)

# excepción de dominio -> (status, code, title, pointer)
MAPEO_DOMINIO: dict[type[ErrorDeDominio], tuple[int, str, str, str | None]] = {
    RecursoNoEncontrado: (404, "RECURSO_NO_ENCONTRADO", "Recurso no encontrado", None),
    AnimalNoDisponible: (409, "ANIMAL_NO_DISPONIBLE", "El animal no está disponible", "/data/relationships/animal"),
    PostulacionDuplicada: (409, "POSTULACION_DUPLICADA", "Postulación duplicada", None),
    PostulacionYaResuelta: (409, "POSTULACION_YA_RESUELTA", "Postulación ya resuelta", None),
    TransicionInvalida: (409, "TRANSICION_INVALIDA", "Cambio de estado no permitido", None),
}

# Mensajes en español por campo, iguales a los del frontend, para mostrarlos junto al input.
MENSAJES_CAMPO = {
    "nombre": "Escribe un nombre válido (máx. 60 caracteres).",
    "especie": "Especie inválida: perro, gato, ave u otro.",
    "edadMeses": "La edad debe ser un entero ≥ 0.",
    "sexo": "Sexo inválido: macho o hembra.",
    "email": "Ingresa un email válido.",
    "telefono": "Teléfono de 7 a 13 dígitos.",
    "ciudad": "Indica tu ciudad.",
    "mensaje": "Cuéntale al refugio por qué (10 a 500 caracteres).",
    "estado": 'El estado debe ser "aprobada" o "rechazada".',
}


def _error(status: int, code: str, title: str, detail: str | None = None,
           source: dict | None = None) -> dict:
    error = {"status": str(status), "code": code, "title": title}
    if detail:
        error["detail"] = detail
    if source:
        error["source"] = source
    return error


def _respuesta(status: int, errores: list[dict]) -> JSONAPIResponse:
    return JSONAPIResponse(status_code=status, content={"errors": errores})


async def _dominio(_: Request, exc: ErrorDeDominio) -> JSONAPIResponse:
    for tipo in type(exc).__mro__:
        if tipo in MAPEO_DOMINIO:
            status, code, title, pointer = MAPEO_DOMINIO[tipo]
            break
    else:
        status, code, title, pointer = 409, "REGLA_DE_NEGOCIO", "Regla de negocio incumplida", None
    source = {"pointer": pointer} if pointer else None
    return _respuesta(status, [_error(status, code, title, str(exc), source)])


async def _solicitud(_: Request, exc: ErrorDeSolicitud) -> JSONAPIResponse:
    return _respuesta(exc.status, [_error(exc.status, exc.code, exc.title, exc.detail, exc.source)])


def _es_malformada(err: dict) -> bool:
    """JSON inválido, sin `data`, o `type` equivocado: el documento no es del recurso esperado."""
    loc = err["loc"]
    return err["type"] == "json_invalid" or loc[-1] == "type" or loc in (("body",), ("body", "data"))


async def _validacion(_: Request, exc: RequestValidationError) -> JSONAPIResponse:
    errores = exc.errors()
    malformados = [e for e in errores if e["loc"][0] == "body" and _es_malformada(e)]
    if malformados:
        e = malformados[0]
        pointer = "/" + "/".join(str(p) for p in e["loc"][1:])
        return _respuesta(400, [_error(400, "SOLICITUD_MALFORMADA", "Documento JSON:API inválido",
                                       e["msg"], {"pointer": pointer or "/"})])

    parametros = [e for e in errores if e["loc"][0] in ("query", "path")]
    if parametros:
        return _respuesta(400, [
            _error(400, "SOLICITUD_MALFORMADA", "Parámetro inválido", e["msg"], {"parameter": str(e["loc"][-1])})
            for e in parametros
        ])

    salida = []
    for e in errores:
        campo = str(e["loc"][-1])
        detalle = "Campo obligatorio." if e["type"] == "missing" else MENSAJES_CAMPO.get(campo, e["msg"])
        pointer = "/" + "/".join(str(p) for p in e["loc"][1:])
        salida.append(_error(422, "VALIDACION", "Campo inválido", detalle, {"pointer": pointer}))
    return _respuesta(422, salida)


async def _validacion_dominio(_: Request, exc: ValidationError) -> JSONAPIResponse:
    """Una entidad rechazó un dato que pasó el borde (p. ej. reglas de forma más estrictas en el
    dominio). Es un error del cliente, no del servidor: 422 en lugar de 500."""
    salida = []
    for e in exc.errors():
        campo = to_camel(str(e["loc"][-1])) if e["loc"] else ""
        detalle = MENSAJES_CAMPO.get(campo, e["msg"])
        source = {"pointer": f"/data/attributes/{campo}"} if campo else None
        salida.append(_error(422, "VALIDACION", "Campo inválido", detalle, source))
    return _respuesta(422, salida)


async def _http(_: Request, exc: StarletteHTTPException) -> JSONAPIResponse:
    codigos = {404: "RECURSO_NO_ENCONTRADO", 405: "METODO_NO_PERMITIDO"}
    code = codigos.get(exc.status_code, "ERROR_HTTP")
    return _respuesta(exc.status_code, [_error(exc.status_code, code, str(exc.detail))])


async def _inesperado(_: Request, exc: Exception) -> JSONAPIResponse:
    log.exception("Error no controlado", exc_info=exc)
    return _respuesta(500, [_error(500, "ERROR_INTERNO", "Error interno del servidor")])


def registrar_manejadores(app: FastAPI) -> None:
    app.add_exception_handler(ErrorDeDominio, _dominio)
    app.add_exception_handler(ErrorDeSolicitud, _solicitud)
    app.add_exception_handler(RequestValidationError, _validacion)
    app.add_exception_handler(ValidationError, _validacion_dominio)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(Exception, _inesperado)
