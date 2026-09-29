"""Traducción entidades de dominio <-> documentos JSON:API 1.1 (docs/contrato-api-jsonapi.md).

Los nombres del contrato (camelCase, `publicadoEn`, fotos como URLs...) solo existen aquí:
el dominio no sabe nada de JSON:API.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.entities import Adoptante, Animal, Postulacion, Refugio

MEDIA_TYPE = "application/vnd.api+json"


class JSONAPIResponse(JSONResponse):
    media_type = MEDIA_TYPE


class ErrorDeSolicitud(Exception):
    """Error del adaptador de entrada (no de dominio): parámetros o formato inválidos."""

    def __init__(self, status: int, code: str, title: str, detail: str | None = None,
                 source: dict[str, str] | None = None):
        super().__init__(detail or title)
        self.status, self.code, self.title, self.detail, self.source = status, code, title, detail, source


def fecha(valor: datetime | None) -> str | None:
    if valor is None:
        return None
    if valor.tzinfo is None:  # Mongo devuelve fechas naive en UTC
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _ref(tipo: str, id_: str) -> dict[str, Any]:
    return {"data": {"type": tipo, "id": id_}}


def animal(a: Animal) -> dict[str, Any]:
    return {
        "type": "animals",
        "id": a.id,
        "attributes": {
            "nombre": a.nombre,
            "especie": a.especie,
            "edadMeses": a.edad_meses,
            "sexo": a.sexo,
            "temperamento": a.temperamento,
            "salud": a.salud.model_dump(),
            "fotos": [f.url for f in a.fotos],
            "detallesEspecie": a.detalles_especie,
            "estado": a.estado,
            "publicadoEn": fecha(a.fecha_publicacion),
        },
        "relationships": {"refugio": _ref("refugios", a.refugio_id)},
    }


def refugio(r: Refugio) -> dict[str, Any]:
    return {
        "type": "refugios",
        "id": r.id,
        "attributes": {
            "nombre": r.nombre,
            "ciudad": r.direccion.ciudad,
            "telefono": r.telefono,
            "email": r.email,
        },
    }


def adoptante(d: Adoptante) -> dict[str, Any]:
    return {
        "type": "adoptantes",
        "id": d.id,
        "attributes": {"nombre": d.nombre, "email": d.email, "telefono": d.telefono, "ciudad": d.ciudad},
    }


def postulacion(p: Postulacion) -> dict[str, Any]:
    return {
        "type": "postulaciones",
        "id": p.id,
        "attributes": {
            "mensaje": p.mensaje,
            "estado": p.estado,
            "motivoCierre": p.motivo_cierre,
            "creadaEn": fecha(p.fecha_postulacion),
            "resueltaEn": fecha(p.fecha_resolucion),
        },
        "relationships": {
            "animal": _ref("animals", p.animal_id),
            "adoptante": _ref("adoptantes", p.adoptante_id),
        },
    }


def documento(data: Any, *, included: list[dict] | None = None, meta: dict | None = None,
              links: dict | None = None) -> dict[str, Any]:
    doc: dict[str, Any] = {"data": data}
    if included is not None:
        doc["included"] = _sin_duplicados(included)
    if meta:
        doc["meta"] = meta
    if links:
        doc["links"] = links
    return doc


def _sin_duplicados(recursos: list[dict]) -> list[dict]:
    vistos, unicos = set(), []
    for r in recursos:
        clave = (r["type"], r["id"])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(r)
    return unicos


def parse_include(valor: str | None, permitidos: set[str]) -> set[str]:
    pedidos = {p.strip() for p in (valor or "").split(",") if p.strip()}
    invalidos = pedidos - permitidos
    if invalidos:
        raise ErrorDeSolicitud(
            400, "SOLICITUD_MALFORMADA", "Relación no soportada en include",
            f"No se puede incluir: {', '.join(sorted(invalidos))}. Permitidas: {', '.join(sorted(permitidos))}.",
            {"parameter": "include"},
        )
    return pedidos


def links_paginacion(request: Request, pagina: int, tamano: int, total: int) -> dict[str, str | None]:
    ultima = max(1, -(-total // tamano))

    def url(n: int) -> str:
        return str(request.url.include_query_params(**{"page[number]": n, "page[size]": tamano}))

    return {
        "self": url(pagina),
        "first": url(1),
        "prev": url(pagina - 1) if pagina > 1 else None,
        "next": url(pagina + 1) if pagina < ultima else None,
        "last": url(ultima),
    }


async def requiere_media_type(request: Request) -> None:
    """Dependencia de POST/PATCH: el contrato exige Content-Type application/vnd.api+json (415)."""
    tipo = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if tipo != MEDIA_TYPE:
        raise ErrorDeSolicitud(
            415, "CONTENT_TYPE_INVALIDO", "Content-Type inválido",
            f"Las peticiones con cuerpo deben usar {MEDIA_TYPE}.",
        )
