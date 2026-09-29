"""Traducción dominio <-> JSON:API, sin levantar la app."""
from datetime import datetime, timezone

import pytest

from app.adapters.inbound.api import jsonapi
from app.adapters.inbound.api.errors import MAPEO_DOMINIO
from app.adapters.inbound.api.schemas import AnimalCrear
from app.domain import exceptions
from app.domain.entities import Animal, Foto, MotivoCierre, Postulacion


def test_fecha_naive_se_asume_utc_y_termina_en_z():
    assert jsonapi.fecha(datetime(2026, 9, 28, 14, 2, 11)) == "2026-09-28T14:02:11Z"
    assert jsonapi.fecha(datetime(2026, 9, 28, 14, 2, 11, tzinfo=timezone.utc)) == "2026-09-28T14:02:11Z"
    assert jsonapi.fecha(None) is None


def test_animal_se_serializa_con_los_nombres_del_contrato():
    a = Animal(id="a1", refugio_id="r1", nombre="Luna", especie="perro", edad_meses=24, sexo="hembra",
               fotos=[Foto(url="http://x/1.jpg", descripcion="en el parque")],
               detalles_especie={"apto_apartamento": True})
    recurso = jsonapi.animal(a)
    assert recurso["type"] == "animals" and recurso["id"] == "a1"
    attrs = recurso["attributes"]
    assert attrs["edadMeses"] == 24
    assert attrs["fotos"] == ["http://x/1.jpg"]  # el contrato define fotos como URLs
    assert attrs["detallesEspecie"] == {"apto_apartamento": True}  # campos libres sin tocar
    assert attrs["publicadoEn"].endswith("Z")
    assert recurso["relationships"]["refugio"] == {"data": {"type": "refugios", "id": "r1"}}


def test_postulacion_se_serializa_con_motivo_y_relaciones():
    p = Postulacion(id="p1", animal_id="a1", adoptante_id="u1", mensaje="Tengo patio grande.")
    p.cerrar_automaticamente()
    recurso = jsonapi.postulacion(p)
    assert recurso["attributes"]["motivoCierre"] == MotivoCierre.CIERRE_AUTOMATICO
    assert recurso["attributes"]["resueltaEn"] is not None
    assert recurso["relationships"]["adoptante"]["data"] == {"type": "adoptantes", "id": "u1"}


def test_included_sin_duplicados():
    r = {"type": "refugios", "id": "r1"}
    assert jsonapi.documento([], included=[r, dict(r)])["included"] == [r]


def test_include_desconocido_es_error_400():
    assert jsonapi.parse_include("refugio, refugio", {"refugio"}) == {"refugio"}
    with pytest.raises(jsonapi.ErrorDeSolicitud) as exc:
        jsonapi.parse_include("refugio,dueño", {"refugio"})
    assert exc.value.status == 400 and exc.value.source == {"parameter": "include"}


def test_toda_excepcion_de_dominio_tiene_codigo_http():
    subclases = set(exceptions.ErrorDeDominio.__subclasses__())
    assert subclases == set(MAPEO_DOMINIO)


def test_documento_de_entrada_se_convierte_en_entidad():
    cuerpo = AnimalCrear.model_validate({"data": {
        "type": "animals",
        "attributes": {"nombre": "  Kiwi ", "especie": "ave", "edadMeses": 12, "sexo": "macho",
                       "estado": "adoptado",  # solo lectura: se ignora
                       "fotos": ["http://x/k.jpg", {"url": "http://x/k2.jpg", "descripcion": "ala"}],
                       "salud": {"vacunado": True, "notas": ""},
                       "detallesEspecie": {"puedeHablar": True}},
        "relationships": {"refugio": {"data": {"type": "refugios", "id": "r2"}}},
    }})
    animal = cuerpo.a_entidad()
    assert animal.nombre == "Kiwi"
    assert animal.refugio_id == "r2"
    assert animal.estado == "disponible"
    assert [f.url for f in animal.fotos] == ["http://x/k.jpg", "http://x/k2.jpg"]
    assert animal.salud.vacunado is True
