"""Revisión cruzada de validaciones: huecos encontrados al comparar frontend y backend."""
import pytest

from tests.integration.api_helpers import JSONAPI, nuevo_animal


def publicar(client, **attrs):
    return client.post("/v1/animals", headers=JSONAPI, json=nuevo_animal(**attrs))


@pytest.mark.parametrize("url", ["javascript:alert(1)", "ftp://x/y.jpg", "no es una url", ""])
def test_foto_con_url_peligrosa_o_invalida_es_422(client, url):
    r = publicar(client, fotos=[url])
    assert r.status_code == 422
    errores = r.json()["errors"]
    assert len(errores) == 1  # un error por campo, aunque `fotos` acepte dos formas
    assert errores[0]["source"]["pointer"] == "/data/attributes/fotos/0"
    assert "URL" in errores[0]["detail"]


def test_foto_como_objeto_invalida_tambien_es_422(client):
    r = publicar(client, fotos=[{"url": "javascript:alert(1)", "descripcion": "x"}])
    assert r.status_code == 422
    assert r.json()["errors"][0]["source"]["pointer"] == "/data/attributes/fotos/0"


@pytest.mark.parametrize("url", ["https://picsum.photos/seed/luna/600/400", "http://x.org/a.png",
                                 "data:image/svg+xml;utf8,%3Csvg%3E%3C/svg%3E"])
def test_fotos_validas_de_la_semilla_y_del_mock(client, url):
    assert publicar(client, fotos=[url]).status_code == 201


@pytest.mark.parametrize("attrs, campo", [
    ({"temperamento": ["x" * 41]}, "temperamento"),
    ({"temperamento": [f"rasgo {i}" for i in range(16)]}, "temperamento"),
    ({"fotos": [f"https://x.org/{i}.jpg" for i in range(11)]}, "fotos"),
    ({"detallesEspecie": {f"k{i}": i for i in range(21)}}, "detallesEspecie"),
])
def test_topes_de_tamano(client, attrs, campo):
    r = publicar(client, **attrs)
    assert r.status_code == 422
    assert r.json()["errors"][0]["source"]["pointer"].startswith(f"/data/attributes/{campo}")


def test_valores_limite_aceptados(client):
    r = publicar(client, nombre="x" * 60, temperamento=["y" * 40] * 15,
                 fotos=[f"https://x.org/{i}.jpg" for i in range(10)],
                 detallesEspecie={f"k{i}": i for i in range(20)})
    assert r.status_code == 201


@pytest.mark.parametrize("telefono, esperado", [
    ("3001112233", 201), ("  3001112233 ", 201),  # el backend recorta espacios; el frontend no los deja
    ("300 111 2233", 422), ("123456", 422), ("12345678901234", 422),
])
def test_telefono_igual_que_en_el_frontend(client, telefono, esperado):
    attrs = {"nombre": "Sofía", "email": f"s{len(telefono)}{esperado}@mail.com", "telefono": telefono, "ciudad": "Cali"}
    r = client.post("/v1/adoptantes", headers=JSONAPI, json={"data": {"type": "adoptantes", "attributes": attrs}})
    assert r.status_code == esperado
