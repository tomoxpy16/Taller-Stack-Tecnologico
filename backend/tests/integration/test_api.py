"""Integración HTTP: peticiones reales a la app completa (routers FastAPI -> casos de uso ->
adaptador in-memory), con los mismos cuerpos que envía el frontend (src/api/httpAdapter.js).

No necesitan Mongo: los repositorios se reemplazan con dependency_overrides, que es justamente
el punto de inyección de la arquitectura hexagonal.
"""
import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.dependencies import crear_repositorios_en_memoria, get_repositorios
from app.domain.entities import Adoptante, Animal, Direccion, Refugio
from app.main import app

JSONAPI = {"Content-Type": "application/vnd.api+json"}
MENSAJE = "Tengo casa con patio y experiencia con perros."


@pytest.fixture
def repos():
    r = crear_repositorios_en_memoria()
    r.refugios._guardar_copia(Refugio(id="huellitas", nombre="Fundación Huellitas", email="h@h.org",
                                      telefono="6015550101", direccion=Direccion(ciudad="Bogotá")))
    r.refugios._guardar_copia(Refugio(id="patitas", nombre="Patitas Felices", email="p@p.org",
                                      direccion=Direccion(ciudad="Medellín")))
    r.adoptantes._guardar_copia(Adoptante(id="ana", nombre="Ana Gómez", email="ana@mail.com",
                                          telefono="3001112233", ciudad="Bogotá"))
    r.adoptantes._guardar_copia(Adoptante(id="carlos", nombre="Carlos Ruiz", email="carlos@mail.com",
                                          telefono="3104445566", ciudad="Bogotá"))
    r.animales._guardar_copia(Animal(id="luna", refugio_id="huellitas", nombre="Luna", especie="perro",
                                     edad_meses=24, sexo="hembra"))
    r.animales._guardar_copia(Animal(id="michi", refugio_id="patitas", nombre="Michi", especie="gato",
                                     edad_meses=8, sexo="macho"))
    return r


@pytest.fixture
def client(repos):
    app.dependency_overrides[get_repositorios] = lambda: repos
    yield TestClient(app)  # sin `with`: no ejecuta el lifespan que conecta a Mongo
    app.dependency_overrides.clear()


def postular(client, animal="luna", adoptante="ana", mensaje=MENSAJE):
    return client.post("/v1/postulaciones", headers=JSONAPI, json={"data": {
        "type": "postulaciones",
        "attributes": {"mensaje": mensaje},
        "relationships": {
            "animal": {"data": {"type": "animals", "id": animal}},
            "adoptante": {"data": {"type": "adoptantes", "id": adoptante}},
        },
    }})


def resolver(client, postulacion_id, estado):
    return client.patch(f"/v1/postulaciones/{postulacion_id}", headers=JSONAPI, json={
        "data": {"type": "postulaciones", "id": postulacion_id, "attributes": {"estado": estado}}
    })


def nuevo_animal(**attrs):
    base = {"nombre": "Toby", "especie": "perro", "edadMeses": 5, "sexo": "macho",
            "temperamento": ["juguetón"], "salud": {"vacunado": True, "esterilizado": False, "notas": ""},
            "fotos": ["https://picsum.photos/seed/toby/600/400"], "detallesEspecie": {"tamano": "pequeño"}}
    return {"data": {"type": "animals", "attributes": base | attrs,
                     "relationships": {"refugio": {"data": {"type": "refugios", "id": "huellitas"}}}}}


def codigo(respuesta):
    return respuesta.json()["errors"][0]["code"]


# --- refugios -------------------------------------------------------------------------

def test_listar_refugios(client):
    r = client.get("/v1/refugios")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.api+json")
    nombres = [x["attributes"]["nombre"] for x in r.json()["data"]]
    assert nombres == ["Fundación Huellitas", "Patitas Felices"]
    assert r.json()["data"][0]["attributes"]["ciudad"] == "Bogotá"


def test_refugio_inexistente_es_404_jsonapi(client):
    r = client.get("/v1/refugios/nada")
    assert r.status_code == 404
    assert codigo(r) == "RECURSO_NO_ENCONTRADO"


# --- animals ----------------------------------------------------------------------------

def test_catalogo_con_include_refugio_meta_y_links(client):
    r = client.get("/v1/animals", params={"include": "refugio", "page[size]": 1})
    cuerpo = r.json()
    assert r.status_code == 200
    assert cuerpo["meta"]["total"] == 2
    assert len(cuerpo["data"]) == 1
    assert cuerpo["links"]["next"] is not None and cuerpo["links"]["prev"] is None
    refugio_id = cuerpo["data"][0]["relationships"]["refugio"]["data"]["id"]
    assert [i["id"] for i in cuerpo["included"]] == [refugio_id]


def test_catalogo_filtra_por_especie_estado_y_refugio(client):
    assert client.get("/v1/animals", params={"filter[especie]": "gato"}).json()["meta"]["total"] == 1
    assert client.get("/v1/animals", params={"filter[refugio]": "huellitas"}).json()["meta"]["total"] == 1
    assert client.get("/v1/animals", params={"filter[estado]": "adoptado"}).json()["meta"]["total"] == 0


@pytest.mark.parametrize("params, parametro", [
    ({"filter[estado]": "perdido"}, "filter[estado]"),
    ({"page[size]": 51}, "page[size]"),
    ({"include": "dueño"}, "include"),
])
def test_parametros_invalidos_son_400(client, params, parametro):
    r = client.get("/v1/animals", params=params)
    assert r.status_code == 400
    assert r.json()["errors"][0]["source"]["parameter"] == parametro


def test_ficha_con_refugio(client):
    r = client.get("/v1/animals/luna", params={"include": "refugio"})
    assert r.json()["data"]["attributes"]["nombre"] == "Luna"
    assert r.json()["included"][0]["type"] == "refugios"


def test_publicar_animal(client):
    r = client.post("/v1/animals", headers=JSONAPI, json=nuevo_animal(estado="adoptado"))
    assert r.status_code == 201
    creado = r.json()["data"]
    assert creado["attributes"]["estado"] == "disponible"  # el estado no lo decide el cliente
    assert r.headers["location"] == f"/v1/animals/{creado['id']}"
    assert client.get(f"/v1/animals/{creado['id']}").status_code == 200


def test_publicar_sin_media_type_jsonapi_es_415(client):
    r = client.post("/v1/animals", json=nuevo_animal())
    assert r.status_code == 415
    assert codigo(r) == "CONTENT_TYPE_INVALIDO"


def test_publicar_con_campos_invalidos_da_un_error_por_campo(client):
    r = client.post("/v1/animals", headers=JSONAPI, json=nuevo_animal(nombre="", edadMeses=-3))
    assert r.status_code == 422
    punteros = {e["source"]["pointer"] for e in r.json()["errors"]}
    assert punteros == {"/data/attributes/nombre", "/data/attributes/edadMeses"}


def test_publicar_con_type_equivocado_es_400(client):
    cuerpo = nuevo_animal()
    cuerpo["data"]["type"] = "gatos"
    assert client.post("/v1/animals", headers=JSONAPI, json=cuerpo).status_code == 400


def test_publicar_en_refugio_inexistente_es_404(client):
    cuerpo = nuevo_animal()
    cuerpo["data"]["relationships"]["refugio"]["data"]["id"] = "fantasma"
    assert client.post("/v1/animals", headers=JSONAPI, json=cuerpo).status_code == 404


def test_json_invalido_es_400(client):
    r = client.post("/v1/animals", headers=JSONAPI, content=b"{no es json")
    assert r.status_code == 400
    assert codigo(r) == "SOLICITUD_MALFORMADA"


# --- adoptantes ---------------------------------------------------------------------------

def test_registrar_adoptante_y_reutilizar_por_email(client):
    datos = {"nombre": "Sofía Díaz", "email": "sofia@mail.com", "telefono": "3005556677", "ciudad": "Cali"}
    primera = client.post("/v1/adoptantes", headers=JSONAPI, json={"data": {"type": "adoptantes", "attributes": datos}})
    segunda = client.post("/v1/adoptantes", headers=JSONAPI,
                          json={"data": {"type": "adoptantes", "attributes": datos | {"email": "SOFIA@mail.com"}}})
    assert (primera.status_code, segunda.status_code) == (201, 200)
    assert primera.json()["data"]["id"] == segunda.json()["data"]["id"]


def test_adoptante_con_telefono_invalido(client):
    datos = {"nombre": "Sofía", "email": "s@mail.com", "telefono": "12", "ciudad": "Cali"}
    r = client.post("/v1/adoptantes", headers=JSONAPI, json={"data": {"type": "adoptantes", "attributes": datos}})
    assert r.status_code == 422
    error = r.json()["errors"][0]
    assert error["source"]["pointer"] == "/data/attributes/telefono"
    assert error["detail"] == "Teléfono de 7 a 13 dígitos."


# --- postulaciones ------------------------------------------------------------------------

def test_postular(client):
    r = postular(client)
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["attributes"]["estado"] == "pendiente"
    assert data["attributes"]["creadaEn"].endswith("Z")
    assert client.get("/v1/animals/luna").json()["data"]["attributes"]["estado"] == "postulado"


def test_mensaje_corto_es_422_con_puntero(client):
    r = postular(client, mensaje="corto")
    assert r.status_code == 422
    assert r.json()["errors"][0]["source"]["pointer"] == "/data/attributes/mensaje"


def test_regla2_postulacion_duplicada_es_409(client):
    postular(client)
    r = postular(client)
    assert r.status_code == 409
    assert codigo(r) == "POSTULACION_DUPLICADA"


def test_regla1_animal_adoptado_es_409_con_puntero(client):
    p = postular(client).json()["data"]["id"]
    resolver(client, p, "aprobada")
    r = postular(client, adoptante="carlos")
    assert r.status_code == 409
    error = r.json()["errors"][0]
    assert error["code"] == "ANIMAL_NO_DISPONIBLE"
    assert error["source"]["pointer"] == "/data/relationships/animal"


def test_listar_postulaciones_del_refugio_con_includes(client):
    postular(client)
    postular(client, animal="michi", adoptante="carlos")
    r = client.get("/v1/postulaciones", params={"filter[refugio]": "huellitas", "include": "animal,adoptante"})
    cuerpo = r.json()
    assert len(cuerpo["data"]) == 1
    assert {(i["type"], i["id"]) for i in cuerpo["included"]} == {("animals", "luna"), ("adoptantes", "ana")}


def test_mis_postulaciones_filtra_por_adoptante_y_estado(client):
    postular(client)
    postular(client, animal="michi")
    assert len(client.get("/v1/postulaciones", params={"filter[adoptante]": "ana"}).json()["data"]) == 2
    params = {"filter[adoptante]": "ana", "filter[estado]": "aprobada"}
    assert client.get("/v1/postulaciones", params=params).json()["data"] == []


def test_listar_postulaciones_sin_filtro_es_400(client):
    assert client.get("/v1/postulaciones").status_code == 400


def test_regla3_aprobar_devuelve_animal_y_cerradas_en_included(client):
    de_ana = postular(client).json()["data"]["id"]
    de_carlos = postular(client, adoptante="carlos").json()["data"]["id"]

    r = resolver(client, de_ana, "aprobada")
    cuerpo = r.json()
    assert r.status_code == 200
    assert cuerpo["data"]["attributes"]["estado"] == "aprobada"
    assert cuerpo["meta"]["postulacionesCerradasAutomaticamente"] == 1
    animal = next(i for i in cuerpo["included"] if i["type"] == "animals")
    cerrada = next(i for i in cuerpo["included"] if i["type"] == "postulaciones")
    assert animal["attributes"]["estado"] == "adoptado"
    assert cerrada["id"] == de_carlos
    assert cerrada["attributes"]["motivoCierre"] == "cierre_automatico"


def test_resolver_dos_veces_es_409(client):
    p = postular(client).json()["data"]["id"]
    resolver(client, p, "rechazada")
    r = resolver(client, p, "aprobada")
    assert r.status_code == 409
    assert codigo(r) == "POSTULACION_YA_RESUELTA"


def test_rechazar_la_unica_pendiente_libera_al_animal(client):
    p = postular(client).json()["data"]["id"]
    r = resolver(client, p, "rechazada")
    assert r.json()["data"]["attributes"]["motivoCierre"] == "rechazada_por_refugio"
    assert r.json()["included"][0]["attributes"]["estado"] == "disponible"


def test_estado_invalido_en_patch_es_422(client):
    p = postular(client).json()["data"]["id"]
    r = resolver(client, p, "pendiente")
    assert r.status_code == 422
    assert r.json()["errors"][0]["source"]["pointer"] == "/data/attributes/estado"


def test_id_del_cuerpo_distinto_al_de_la_url_es_409(client):
    p = postular(client).json()["data"]["id"]
    r = client.patch(f"/v1/postulaciones/{p}", headers=JSONAPI,
                     json={"data": {"type": "postulaciones", "id": "otro", "attributes": {"estado": "aprobada"}}})
    assert r.status_code == 409


def test_ruta_inexistente_responde_error_jsonapi(client):
    r = client.get("/v1/no-existe")
    assert r.status_code == 404
    assert "errors" in r.json()


# --- flujo end-to-end, tal como lo recorre el frontend -------------------------------------

def test_flujo_completo_por_http(client):
    # 1. El refugio publica un animal
    rocky = client.post("/v1/animals", headers=JSONAPI, json=nuevo_animal(nombre="Rocky")).json()["data"]["id"]
    # 2. Dos adoptantes se registran y postulan
    ids = []
    for nombre, email in (("Valentina Mora", "vale@mail.com"), ("Pedro Pérez", "pedro@mail.com")):
        attrs = {"nombre": nombre, "email": email, "telefono": "3207778899", "ciudad": "Medellín"}
        adoptante = client.post("/v1/adoptantes", headers=JSONAPI,
                                json={"data": {"type": "adoptantes", "attributes": attrs}}).json()["data"]["id"]
        ids.append(postular(client, animal=rocky, adoptante=adoptante).json()["data"]["id"])
    # 3. El refugio ve ambas en su panel
    panel = client.get("/v1/postulaciones", params={"filter[refugio]": "huellitas", "filter[estado]": "pendiente"})
    assert {p["id"] for p in panel.json()["data"]} == set(ids)
    # 4-5. Aprueba la primera: Rocky adoptado y la otra cerrada sola
    r = resolver(client, ids[0], "aprobada").json()
    assert r["meta"]["postulacionesCerradasAutomaticamente"] == 1
    ficha = client.get(f"/v1/animals/{rocky}").json()["data"]
    assert ficha["attributes"]["estado"] == "adoptado"
