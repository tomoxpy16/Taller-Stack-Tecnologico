"""PATCH /v1/postulaciones/{id}: aprobar/rechazar y cierre automático (regla 3), verificando
también lo que ve cada usuario después, con las mismas consultas que hace el frontend."""
from app.domain.entities import Adoptante, EstadoAnimal, EstadoPostulacion, MotivoCierre, Postulacion
from tests.integration.api_helpers import postular, resolver


def mis_postulaciones(client, adoptante):
    r = client.get("/v1/postulaciones", params={"filter[adoptante]": adoptante, "include": "animal"})
    return {p["id"]: p["attributes"] for p in r.json()["data"]}


def ids(respuesta, tipo):
    return {i["id"] for i in respuesta.json()["included"] if i["type"] == tipo}


async def test_aprobar_cierra_todas_las_demas_pendientes(client, repos):
    repos.adoptantes._guardar_copia(Adoptante(id="vale", nombre="Valentina", email="vale@mail.com",
                                              telefono="3207778899", ciudad="Medellín"))
    de_ana = postular(client).json()["data"]["id"]
    de_carlos = postular(client, adoptante="carlos").json()["data"]["id"]
    de_vale = postular(client, adoptante="vale").json()["data"]["id"]

    r = resolver(client, de_carlos, "aprobada")

    assert r.status_code == 200
    assert ids(r, "postulaciones") == {de_ana, de_vale}
    assert r.json()["meta"]["postulacionesCerradasAutomaticamente"] == 2
    pendientes = await repos.postulaciones.listar_por_animal("luna", estado=EstadoPostulacion.PENDIENTE)
    assert pendientes == []


def test_cada_adoptante_ve_el_resultado_en_mis_postulaciones(client):
    de_ana = postular(client).json()["data"]["id"]
    de_carlos = postular(client, adoptante="carlos").json()["data"]["id"]

    resolver(client, de_ana, "aprobada")

    ana = mis_postulaciones(client, "ana")[de_ana]
    carlos = mis_postulaciones(client, "carlos")[de_carlos]
    assert (ana["estado"], ana["motivoCierre"]) == ("aprobada", None)
    assert (carlos["estado"], carlos["motivoCierre"]) == ("rechazada", "cierre_automatico")
    assert ana["resueltaEn"] is not None and carlos["resueltaEn"] is not None


def test_el_panel_del_refugio_queda_consistente(client):
    de_ana = postular(client).json()["data"]["id"]
    postular(client, adoptante="carlos")

    resolver(client, de_ana, "aprobada")

    panel = client.get("/v1/postulaciones", params={"filter[refugio]": "huellitas", "include": "animal"}).json()
    estados = sorted(p["attributes"]["estado"] for p in panel["data"])
    assert estados == ["aprobada", "rechazada"]
    assert panel["included"][0]["attributes"]["estado"] == "adoptado"


async def test_una_rechazada_antes_conserva_su_motivo(client, repos):
    de_ana = postular(client).json()["data"]["id"]
    de_carlos = postular(client, adoptante="carlos").json()["data"]["id"]
    resolver(client, de_carlos, "rechazada")

    r = resolver(client, de_ana, "aprobada")

    assert r.json()["meta"]["postulacionesCerradasAutomaticamente"] == 0
    carlos = await repos.postulaciones.obtener(de_carlos)
    assert carlos.motivo_cierre == MotivoCierre.RECHAZADA_POR_REFUGIO  # no se reescribe como automático


def test_aprobar_la_unica_pendiente_no_cierra_nada(client):
    r = resolver(client, postular(client).json()["data"]["id"], "aprobada")
    assert r.json()["meta"]["postulacionesCerradasAutomaticamente"] == 0
    assert [i["type"] for i in r.json()["included"]] == ["animals"]


def test_aprobar_no_toca_las_postulaciones_de_otro_animal(client):
    de_ana = postular(client).json()["data"]["id"]
    a_michi = postular(client, animal="michi", adoptante="carlos").json()["data"]["id"]

    resolver(client, de_ana, "aprobada")

    assert mis_postulaciones(client, "carlos")[a_michi]["estado"] == "pendiente"
    assert client.get("/v1/animals/michi").json()["data"]["attributes"]["estado"] == "postulado"


def test_rechazar_no_cierra_las_demas(client):
    de_ana = postular(client).json()["data"]["id"]
    de_carlos = postular(client, adoptante="carlos").json()["data"]["id"]

    r = resolver(client, de_ana, "rechazada")

    assert r.json()["meta"]["postulacionesCerradasAutomaticamente"] == 0
    assert mis_postulaciones(client, "carlos")[de_carlos]["estado"] == "pendiente"
    assert r.json()["included"][0]["attributes"]["estado"] == "postulado"


def test_una_cerrada_automaticamente_no_se_puede_aprobar(client):
    de_ana = postular(client).json()["data"]["id"]
    de_carlos = postular(client, adoptante="carlos").json()["data"]["id"]
    resolver(client, de_ana, "aprobada")

    r = resolver(client, de_carlos, "aprobada")

    assert r.status_code == 409
    assert r.json()["errors"][0]["code"] == "POSTULACION_YA_RESUELTA"


async def test_pendiente_huerfana_sobre_animal_adoptado_no_se_puede_aprobar(client, repos):
    # Estado que dejaría una falla a mitad del cierre automático: el animal ya está adoptado
    # pero queda una pendiente. No debe poder aprobarse (habría dos dueños)...
    resolver(client, postular(client).json()["data"]["id"], "aprobada")
    huerfana = await repos.postulaciones.guardar(
        Postulacion(animal_id="luna", adoptante_id="carlos", mensaje="Quedó pendiente por una falla.")
    )
    r = resolver(client, huerfana.id, "aprobada")
    assert r.status_code == 409
    assert r.json()["errors"][0]["code"] == "TRANSICION_INVALIDA"

    # ...pero sí rechazarse, sin "liberar" al animal adoptado.
    r = resolver(client, huerfana.id, "rechazada")
    assert r.status_code == 200
    assert (await repos.animales.obtener("luna")).estado == EstadoAnimal.ADOPTADO
