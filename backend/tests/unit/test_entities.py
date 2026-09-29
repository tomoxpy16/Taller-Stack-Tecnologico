import pytest
from pydantic import ValidationError

from app.domain.entities import (
    Animal,
    Especie,
    EstadoAnimal,
    EstadoPostulacion,
    MotivoCierre,
    Postulacion,
    Sexo,
)
from app.domain.exceptions import AnimalNoDisponible, PostulacionYaResuelta, TransicionInvalida


def nuevo_animal(**cambios) -> Animal:
    datos = dict(refugio_id="r1", nombre="Luna", especie=Especie.PERRO, edad_meses=24, sexo=Sexo.HEMBRA)
    return Animal(**(datos | cambios))


def nueva_postulacion(**cambios) -> Postulacion:
    datos = dict(animal_id="a1", adoptante_id="u1", mensaje="Tengo patio grande y experiencia.")
    return Postulacion(**(datos | cambios))


# --- Forma (Pydantic) ---------------------------------------------------------

def test_animal_nuevo_arranca_disponible_y_sin_id():
    animal = nuevo_animal()
    assert animal.estado == EstadoAnimal.DISPONIBLE
    assert animal.id is None


def test_detalles_especie_acepta_campos_libres():
    ave = nuevo_animal(especie="ave", detalles_especie={"habla": True, "requiere_jaula": True})
    assert ave.detalles_especie["habla"] is True


@pytest.mark.parametrize("cambio", [{"edad_meses": -1}, {"nombre": ""}, {"especie": "dragon"}])
def test_animal_rechaza_datos_invalidos(cambio):
    with pytest.raises(ValidationError):
        nuevo_animal(**cambio)


def test_mensaje_de_postulacion_debe_tener_al_menos_10_caracteres():
    with pytest.raises(ValidationError):
        nueva_postulacion(mensaje="corto")


def test_asignar_estado_invalido_tambien_falla():
    animal = nuevo_animal()
    with pytest.raises(ValidationError):
        animal.estado = "perdido"


# --- Reglas del animal ----------------------------------------------------------

def test_primera_postulacion_pasa_el_animal_a_postulado():
    animal = nuevo_animal()
    animal.registrar_postulacion()
    assert animal.estado == EstadoAnimal.POSTULADO


def test_animal_postulado_sigue_recibiendo_postulaciones():
    animal = nuevo_animal(estado=EstadoAnimal.POSTULADO)
    animal.registrar_postulacion()
    assert animal.estado == EstadoAnimal.POSTULADO


def test_regla1_no_se_postula_a_un_animal_adoptado():
    animal = nuevo_animal(estado=EstadoAnimal.ADOPTADO)
    with pytest.raises(AnimalNoDisponible):
        animal.registrar_postulacion()


def test_solo_se_adopta_un_animal_postulado():
    with pytest.raises(TransicionInvalida):
        nuevo_animal().marcar_adoptado()


def test_animal_postulado_vuelve_a_disponible_al_liberarse():
    animal = nuevo_animal(estado=EstadoAnimal.POSTULADO)
    animal.liberar()
    assert animal.estado == EstadoAnimal.DISPONIBLE


# --- Reglas de la postulación -----------------------------------------------------

def test_aprobar_resuelve_la_postulacion():
    postulacion = nueva_postulacion()
    postulacion.aprobar()
    assert postulacion.estado == EstadoPostulacion.APROBADA
    assert postulacion.fecha_resolucion is not None
    assert postulacion.motivo_cierre is None


def test_rechazo_del_refugio_guarda_el_motivo():
    postulacion = nueva_postulacion()
    postulacion.rechazar()
    assert postulacion.estado == EstadoPostulacion.RECHAZADA
    assert postulacion.motivo_cierre == MotivoCierre.RECHAZADA_POR_REFUGIO


def test_regla3_cierre_automatico():
    postulacion = nueva_postulacion()
    postulacion.cerrar_automaticamente()
    assert postulacion.estado == EstadoPostulacion.RECHAZADA
    assert postulacion.motivo_cierre == MotivoCierre.CIERRE_AUTOMATICO


@pytest.mark.parametrize("accion", ["aprobar", "rechazar", "cerrar_automaticamente"])
def test_una_postulacion_resuelta_no_se_vuelve_a_resolver(accion):
    postulacion = nueva_postulacion()
    postulacion.aprobar()
    with pytest.raises(PostulacionYaResuelta):
        getattr(postulacion, accion)()
