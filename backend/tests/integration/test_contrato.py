"""El contrato cerrado (docs/contrato-api-jsonapi.md) y el código no pueden divergir.

Compara la tabla de endpoints del contrato con las rutas reales de FastAPI y con las que llama
el frontend (src/api/httpAdapter.js), y verifica que todo código de error del dominio esté
documentado. Si alguien cambia una ruta sin actualizar el contrato (o al revés), falla.
Necesita el repositorio completo: se omite si solo está montado backend/.
"""
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.adapters.inbound.api.errors import MAPEO_DOMINIO
from app.main import app

RAIZ = Path(__file__).resolve().parents[3]
CONTRATO = RAIZ / "docs" / "contrato-api-jsonapi.md"
FRONTEND = RAIZ / "frontend" / "src" / "api" / "httpAdapter.js"

pytestmark = pytest.mark.skipif(not CONTRATO.exists(), reason="requiere el repo completo (docs/)")


def normalizar(ruta: str) -> str:
    """/animals/{animal_id}?include=x -> /animals/{}"""
    return re.sub(r"\{[^}]*\}", "{}", ruta.split("?")[0].rstrip("/") or "/")


def endpoints_del_contrato() -> set[tuple[str, str]]:
    filas = re.findall(r"^\| (GET|POST|PATCH|PUT|DELETE) \| `([^`]+)` \|", CONTRATO.read_text(encoding="utf-8"), re.M)
    return {(metodo, normalizar(ruta)) for metodo, ruta in filas}


def endpoints_de_la_app() -> set[tuple[str, str]]:
    rutas = set()
    for r in app.routes:
        if isinstance(r, APIRoute) and r.path.startswith("/v1"):
            for metodo in r.methods:
                rutas.add((metodo, normalizar(r.path.removeprefix("/v1"))))
    return rutas


def test_el_contrato_esta_cerrado():
    texto = CONTRATO.read_text(encoding="utf-8")
    assert "v1.0" in texto.splitlines()[0]
    assert "Decisiones que hay que cerrar" not in texto


def test_cada_endpoint_del_contrato_existe_en_la_app():
    faltan = endpoints_del_contrato() - endpoints_de_la_app()
    assert not faltan, f"El contrato promete endpoints que la app no tiene: {sorted(faltan)}"


def test_la_app_no_expone_endpoints_fuera_del_contrato():
    sobran = endpoints_de_la_app() - endpoints_del_contrato()
    assert not sobran, f"Endpoints sin documentar en el contrato: {sorted(sobran)}"


def test_el_frontend_solo_llama_endpoints_del_contrato():
    if not FRONTEND.exists():
        pytest.skip("frontend no disponible")
    js = FRONTEND.read_text(encoding="utf-8")
    llamadas = {(m, normalizar(re.sub(r"\$\{[^}]+\}", "{x}", ruta)))
                for m, ruta in re.findall(r"request\('(GET|POST|PATCH)', [`']([^`']+)[`']", js)}
    assert llamadas, "no se encontraron llamadas en httpAdapter.js"
    assert llamadas <= endpoints_del_contrato(), sorted(llamadas - endpoints_del_contrato())


def test_todo_codigo_de_error_del_dominio_esta_en_el_contrato():
    documentados = set(re.findall(r"^\| \d{3} \| `([A-Z_]+)` \|", CONTRATO.read_text(encoding="utf-8"), re.M))
    emitidos = {code for _, code, _, _ in MAPEO_DOMINIO.values()} | {
        "SOLICITUD_MALFORMADA", "CONTENT_TYPE_INVALIDO", "VALIDACION", "ID_NO_COINCIDE",
        "METODO_NO_PERMITIDO", "ERROR_INTERNO",
    }
    assert emitidos <= documentados, f"Códigos sin documentar: {sorted(emitidos - documentados)}"
