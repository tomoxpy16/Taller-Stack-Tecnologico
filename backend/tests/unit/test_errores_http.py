"""Mapeo excepción -> respuesta de error JSON:API, probando los manejadores sin levantar la app."""
import json

import pytest
from pydantic import ValidationError

from app.adapters.inbound.api import errors
from app.domain.entities import Animal, Postulacion
from app.domain.exceptions import (
    AnimalNoDisponible,
    ErrorDeDominio,
    PostulacionDuplicada,
    PostulacionYaResuelta,
    RecursoNoEncontrado,
    TransicionInvalida,
)


async def responder(manejador, exc):
    respuesta = await manejador(None, exc)
    return respuesta.status_code, json.loads(respuesta.body)["errors"]


@pytest.mark.parametrize("excepcion, status, code", [
    (AnimalNoDisponible, 409, "ANIMAL_NO_DISPONIBLE"),
    (PostulacionDuplicada, 409, "POSTULACION_DUPLICADA"),
    (PostulacionYaResuelta, 409, "POSTULACION_YA_RESUELTA"),
    (RecursoNoEncontrado, 404, "RECURSO_NO_ENCONTRADO"),
    (TransicionInvalida, 409, "TRANSICION_INVALIDA"),
])
async def test_cada_excepcion_de_dominio_tiene_su_codigo(excepcion, status, code):
    http, [error] = await responder(errors._dominio, excepcion("detalle del dominio"))
    assert http == status
    assert error["status"] == str(status)  # JSON:API exige status como string
    assert error["code"] == code
    assert error["detail"] == "detalle del dominio"


async def test_animal_no_disponible_apunta_a_la_relacion():
    _, [error] = await responder(errors._dominio, AnimalNoDisponible("x"))
    assert error["source"] == {"pointer": "/data/relationships/animal"}


async def test_subclase_hereda_el_codigo_de_su_padre():
    class AnimalEnCuarentena(AnimalNoDisponible):
        pass

    http, [error] = await responder(errors._dominio, AnimalEnCuarentena("x"))
    assert (http, error["code"]) == (409, "ANIMAL_NO_DISPONIBLE")


async def test_regla_nueva_sin_mapeo_es_409_generico_y_no_500():
    class ReglaNueva(ErrorDeDominio):
        pass

    http, [error] = await responder(errors._dominio, ReglaNueva("x"))
    assert (http, error["code"]) == (409, "REGLA_DE_NEGOCIO")


async def test_validacion_del_dominio_es_422_con_puntero_en_camel_case():
    with pytest.raises(ValidationError) as exc:
        Animal(refugio_id="r", nombre="Luna", especie="perro", edad_meses=-1, sexo="hembra")
    http, [error] = await responder(errors._validacion_dominio, exc.value)
    assert http == 422
    assert error["source"] == {"pointer": "/data/attributes/edadMeses"}
    assert error["detail"] == errors.MENSAJES_CAMPO["edadMeses"]


async def test_error_inesperado_es_500_sin_filtrar_detalles():
    http, [error] = await responder(errors._inesperado, RuntimeError("password=secreto"))
    assert (http, error["code"]) == (500, "ERROR_INTERNO")
    assert "secreto" not in json.dumps(error)


# --- Mensajes que ve el usuario ---------------------------------------------------------

@pytest.mark.parametrize("sexo, texto", [("hembra", "Luna ya fue adoptada."), ("macho", "Luna ya fue adoptado.")])
def test_mensaje_de_animal_no_disponible_concuerda_con_el_sexo(sexo, texto):
    animal = Animal(refugio_id="r", nombre="Luna", especie="perro", edad_meses=3, sexo=sexo, estado="adoptado")
    with pytest.raises(AnimalNoDisponible, match=texto):
        animal.validar_postulable()


def test_postulacion_ya_resuelta_dice_en_que_estado_quedo():
    p = Postulacion(animal_id="a", adoptante_id="u", mensaje="Tengo patio grande.")
    p.aprobar()
    with pytest.raises(PostulacionYaResuelta, match="aprobada"):
        p.rechazar()
