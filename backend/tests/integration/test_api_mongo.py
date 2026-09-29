"""Integración completa: routers FastAPI -> casos de uso -> adaptador MongoDB -> Mongo real.
Recorre el flujo principal del README con los mismos cuerpos que envía el frontend.

Usa httpx.AsyncClient (no TestClient) para que la app corra en el mismo event loop que Motor."""
import httpx
import pytest
from bson import ObjectId

from app.adapters.inbound.api.dependencies import crear_repositorios_mongo, get_repositorios
from app.main import app
from tests.integration.api_helpers import JSONAPI, MENSAJE

pytestmark = pytest.mark.integration


@pytest.fixture
async def api(mongo_db):
    refugio = await mongo_db.refugios.insert_one(
        {"nombre": "Fundación Huellitas", "email": "h@h.org", "direccion": {"ciudad": "Bogotá"}}
    )
    rocky = await mongo_db.animales.insert_one({
        "refugio_id": refugio.inserted_id, "nombre": "Rocky", "especie": "perro", "edad_meses": 60,
        "sexo": "macho", "estado": "disponible",
    })
    adoptantes = await mongo_db.adoptantes.insert_many([
        {"nombre": "Ana Gómez", "email": "ana@mail.com", "telefono": "3001112233", "ciudad": "Bogotá"},
        {"nombre": "Carlos Ruiz", "email": "carlos@mail.com", "telefono": "3104445566", "ciudad": "Bogotá"},
    ])

    app.dependency_overrides[get_repositorios] = lambda: crear_repositorios_mongo(mongo_db)
    transporte = httpx.ASGITransport(app=app)  # no ejecuta el lifespan: la base la da el fixture
    async with httpx.AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente, {
            "refugio": str(refugio.inserted_id),
            "rocky": str(rocky.inserted_id),
            "ana": str(adoptantes.inserted_ids[0]),
            "carlos": str(adoptantes.inserted_ids[1]),
        }
    app.dependency_overrides.clear()


async def _postular(cliente, animal, adoptante):
    return await cliente.post("/v1/postulaciones", headers=JSONAPI, json={"data": {
        "type": "postulaciones",
        "attributes": {"mensaje": MENSAJE},
        "relationships": {
            "animal": {"data": {"type": "animals", "id": animal}},
            "adoptante": {"data": {"type": "adoptantes", "id": adoptante}},
        },
    }})


async def test_catalogo_y_ficha_desde_mongo(api):
    cliente, ids = api
    r = await cliente.get("/v1/animals", params={"include": "refugio"})
    assert r.status_code == 200
    assert r.json()["meta"]["total"] == 1
    assert r.json()["data"][0]["id"] == ids["rocky"]
    assert r.json()["included"][0]["id"] == ids["refugio"]

    assert (await cliente.get(f"/v1/animals/{ids['rocky']}")).json()["data"]["attributes"]["nombre"] == "Rocky"
    assert (await cliente.get(f"/v1/animals/{ObjectId()}")).status_code == 404
    assert (await cliente.get("/v1/animals/no-es-un-id")).status_code == 404


async def test_flujo_completo_aprobar_cierra_las_demas(api, mongo_db):
    cliente, ids = api
    r_ana = await _postular(cliente, ids["rocky"], ids["ana"])
    r_carlos = await _postular(cliente, ids["rocky"], ids["carlos"])
    assert r_ana.status_code == 201 and r_carlos.status_code == 201
    assert (await mongo_db.animales.find_one({"_id": ObjectId(ids["rocky"])}))["estado"] == "postulado"

    duplicada = await _postular(cliente, ids["rocky"], ids["ana"])
    assert duplicada.status_code == 409
    assert duplicada.json()["errors"][0]["code"] == "POSTULACION_DUPLICADA"

    id_ana = r_ana.json()["data"]["id"]
    r = await cliente.patch(f"/v1/postulaciones/{id_ana}", headers=JSONAPI, json={
        "data": {"type": "postulaciones", "id": id_ana, "attributes": {"estado": "aprobada"}}
    })
    assert r.status_code == 200
    assert r.json()["data"]["attributes"]["estado"] == "aprobada"
    assert r.json()["meta"]["postulacionesCerradasAutomaticamente"] == 1

    # Lo que quedó persistido en Mongo, no solo lo que respondió la API.
    assert (await mongo_db.animales.find_one({"_id": ObjectId(ids["rocky"])}))["estado"] == "adoptado"
    carlos = await mongo_db.postulaciones.find_one({"_id": ObjectId(r_carlos.json()["data"]["id"])})
    assert carlos["estado"] == "rechazada" and carlos["motivo_cierre"] == "cierre_automatico"

    tarde = await _postular(cliente, ids["rocky"], ids["carlos"])
    assert tarde.status_code == 409
    assert tarde.json()["errors"][0]["code"] == "ANIMAL_NO_DISPONIBLE"


async def test_panel_del_refugio_lista_sus_postulaciones(api):
    cliente, ids = api
    await _postular(cliente, ids["rocky"], ids["ana"])
    r = await cliente.get("/v1/postulaciones", params={"filter[refugio]": ids["refugio"], "include": "animal,adoptante"})
    assert r.status_code == 200
    assert len(r.json()["data"]) == 1
    assert {i["type"] for i in r.json()["included"]} == {"animals", "adoptantes"}
