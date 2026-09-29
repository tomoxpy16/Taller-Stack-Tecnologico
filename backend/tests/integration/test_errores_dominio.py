"""Integración HTTP de las dos validaciones de la tarea: no postular a un animal no disponible
(regla 1) y no duplicar una postulación activa (regla 2). Se verifica el documento de error
completo y, sobre todo, que un rechazo no deje datos a medias."""
from fastapi.testclient import TestClient

from app.adapters.inbound.api import postulaciones as router_postulaciones
from app.domain.entities import EstadoAnimal, Postulacion
from app.main import app
from tests.integration.api_helpers import postular, resolver


async def estado_de(repos, animal_id):
    return (await repos.animales.obtener(animal_id)).estado


# --- Regla 1: animal no disponible ----------------------------------------------------------

async def test_regla1_documento_de_error_completo(client, repos):
    resolver(client, postular(client).json()["data"]["id"], "aprobada")

    r = postular(client, adoptante="carlos")

    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/vnd.api+json")
    assert r.json() == {"errors": [{
        "status": "409",
        "code": "ANIMAL_NO_DISPONIBLE",
        "title": "El animal no está disponible",
        "detail": "Luna ya fue adoptada.",
        "source": {"pointer": "/data/relationships/animal"},
    }]}


async def test_regla1_el_rechazo_no_guarda_nada(client, repos):
    resolver(client, postular(client).json()["data"]["id"], "aprobada")
    antes = await repos.postulaciones.listar_por_animal("luna")

    postular(client, adoptante="carlos")

    assert await repos.postulaciones.listar_por_animal("luna") == antes
    assert await repos.postulaciones.listar_por_adoptante("carlos") == []
    assert await estado_de(repos, "luna") == EstadoAnimal.ADOPTADO


async def test_animal_postulado_si_acepta_mas_postulaciones(client, repos):
    postular(client)
    assert await estado_de(repos, "luna") == EstadoAnimal.POSTULADO
    assert postular(client, adoptante="carlos").status_code == 201


async def test_animal_liberado_tras_rechazo_vuelve_a_aceptar(client, repos):
    resolver(client, postular(client).json()["data"]["id"], "rechazada")
    assert await estado_de(repos, "luna") == EstadoAnimal.DISPONIBLE
    assert postular(client, adoptante="carlos").status_code == 201


# --- Regla 2: postulación activa duplicada -------------------------------------------------

async def test_regla2_documento_de_error_completo(client):
    postular(client)

    r = postular(client)

    assert r.status_code == 409
    assert r.json() == {"errors": [{
        "status": "409",
        "code": "POSTULACION_DUPLICADA",
        "title": "Postulación duplicada",
        "detail": "Ya tienes una postulación pendiente para Luna.",
    }]}


async def test_regla2_el_rechazo_no_guarda_una_segunda_postulacion(client, repos):
    postular(client)
    postular(client)
    postular(client)
    assert len(await repos.postulaciones.listar_por_adoptante("ana")) == 1


async def test_regla2_solo_cuenta_la_postulacion_activa(client):
    # Rechazada ya no está activa: puede volver a postular
    resolver(client, postular(client).json()["data"]["id"], "rechazada")
    assert postular(client).status_code == 201


async def test_regla2_es_por_animal(client):
    postular(client)
    assert postular(client, animal="michi").status_code == 201


async def test_regla1_se_evalua_antes_que_la_regla2(client):
    # Ana tenía una pendiente cerrada automáticamente; Luna ya fue adoptada por Carlos.
    postular(client)
    resolver(client, postular(client, adoptante="carlos").json()["data"]["id"], "aprobada")
    assert postular(client).json()["errors"][0]["code"] == "ANIMAL_NO_DISPONIBLE"


# --- Errores que no son reglas de negocio ---------------------------------------------------

def test_recurso_inexistente_en_la_relacion_es_404(client):
    r = postular(client, animal="fantasma")
    assert r.status_code == 404
    assert r.json()["errors"][0]["detail"] == "No existe el animal fantasma."


def test_validacion_que_falla_en_el_dominio_es_422_y_no_500(client, monkeypatch):
    class PostularQueFallaEnElDominio:
        def __init__(self, *_):
            pass

        async def ejecutar(self, **_):
            Postulacion(animal_id="luna", adoptante_id="ana", mensaje="corto")  # ValidationError

    monkeypatch.setattr(router_postulaciones, "Postular", PostularQueFallaEnElDominio)
    r = postular(client)
    assert r.status_code == 422
    assert r.json()["errors"][0]["source"]["pointer"] == "/data/attributes/mensaje"


def test_error_inesperado_es_500_jsonapi(client, monkeypatch):
    class PostularRoto:
        def __init__(self, *_):
            pass

        async def ejecutar(self, **_):
            raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(router_postulaciones, "Postular", PostularRoto)
    r = TestClient(app, raise_server_exceptions=False).post(
        "/v1/postulaciones", headers={"Content-Type": "application/vnd.api+json"},
        json={"data": {"type": "postulaciones", "attributes": {"mensaje": "Tengo patio grande."},
                       "relationships": {"animal": {"data": {"type": "animals", "id": "luna"}},
                                         "adoptante": {"data": {"type": "adoptantes", "id": "ana"}}}}},
    )
    assert r.status_code == 500
    assert r.json() == {"errors": [{"status": "500", "code": "ERROR_INTERNO", "title": "Error interno del servidor"}]}
