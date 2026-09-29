"""Cliente HTTP de prueba y cuerpos JSON:API iguales a los del frontend (src/api/httpAdapter.js).

Los repositorios se reemplazan con dependency_overrides: es el punto de inyección de la
arquitectura hexagonal, así que la app completa corre sin Mongo.
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
