"""Casos de uso probados con el adaptador in-memory: sin Mongo, sin FastAPI, en milisegundos."""
import pytest

from app.adapters.outbound.persistence.memory import (
    InMemoryAdoptanteRepository,
    InMemoryAnimalRepository,
    InMemoryPostulacionRepository,
    InMemoryRefugioRepository,
)
from app.application.ports import (
    AdoptanteRepository,
    AnimalRepository,
    PostulacionRepository,
    RefugioRepository,
)
from app.application.use_cases import (
    AprobarPostulacion,
    ConsultarAnimal,
    ListarAnimales,
    ListarPostulaciones,
    Postular,
    PublicarAnimal,
    RechazarPostulacion,
    RegistrarAdoptante,
)
from app.domain.entities import (
    Adoptante,
    Animal,
    Direccion,
    EstadoAnimal,
    EstadoPostulacion,
    MotivoCierre,
    Refugio,
)
from app.domain.exceptions import (
    AnimalNoDisponible,
    PostulacionDuplicada,
    PostulacionYaResuelta,
    RecursoNoEncontrado,
)

MENSAJE = "Tengo patio grande y experiencia con perros."


@pytest.fixture
def animales():
    return InMemoryAnimalRepository()


@pytest.fixture
def postulaciones(animales):
    return InMemoryPostulacionRepository(animales)


@pytest.fixture
def refugios():
    return InMemoryRefugioRepository([
        Refugio(id=i, nombre=i.title(), email=f"{i}@refugio.org", direccion=Direccion(ciudad="Bogotá"))
        for i in ("huellitas", "patitas", "r", "r1", "r2")
    ])


@pytest.fixture
def adoptantes():
    return InMemoryAdoptanteRepository([
        Adoptante(id=i, nombre=i.title(), email=f"{i}@mail.com", telefono="3001112233", ciudad="Bogotá")
        for i in ("ana", "carlos", "vale")
    ])


@pytest.fixture
async def luna(animales, refugios):
    animal = Animal(refugio_id="huellitas", nombre="Luna", especie="perro", edad_meses=24, sexo="hembra")
    return await PublicarAnimal(animales, refugios).ejecutar(animal)


@pytest.fixture
def postular(animales, postulaciones, adoptantes):
    return Postular(animales, postulaciones, adoptantes).ejecutar


def test_los_adaptadores_in_memory_cumplen_los_puertos(animales, postulaciones, refugios, adoptantes):
    assert isinstance(animales, AnimalRepository)
    assert isinstance(postulaciones, PostulacionRepository)
    assert isinstance(refugios, RefugioRepository)
    assert isinstance(adoptantes, AdoptanteRepository)


# --- Animales -------------------------------------------------------------------

async def test_publicar_asigna_id_y_fuerza_estado_disponible(animales, refugios):
    animal = Animal(refugio_id="r", nombre="Kiwi", especie="ave", edad_meses=8, sexo="macho",
                    estado=EstadoAnimal.ADOPTADO)
    publicado = await PublicarAnimal(animales, refugios).ejecutar(animal)
    assert publicado.id is not None
    assert publicado.estado == EstadoAnimal.DISPONIBLE


async def test_consultar_animal_inexistente(animales):
    with pytest.raises(RecursoNoEncontrado):
        await ConsultarAnimal(animales).ejecutar("no-existe")


async def test_listar_filtra_y_pagina(animales, refugios):
    publicar = PublicarAnimal(animales, refugios).ejecutar
    for i in range(5):
        await publicar(Animal(refugio_id="r1", nombre=f"Perro {i}", especie="perro", edad_meses=i, sexo="macho"))
    await publicar(Animal(refugio_id="r2", nombre="Michi", especie="gato", edad_meses=3, sexo="hembra"))

    pagina, total = await ListarAnimales(animales).ejecutar(especie="perro", pagina=2, tamano=2)
    assert total == 5
    assert len(pagina) == 2
    _, total_r2 = await ListarAnimales(animales).ejecutar(refugio_id="r2")
    assert total_r2 == 1


# --- Postular (reglas 1 y 2) ------------------------------------------------------

async def test_postular_crea_pendiente_y_pasa_animal_a_postulado(animales, luna, postular):
    postulacion = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    assert postulacion.id is not None
    assert postulacion.estado == EstadoPostulacion.PENDIENTE
    assert (await animales.obtener(luna.id)).estado == EstadoAnimal.POSTULADO


async def test_postular_a_animal_inexistente(postular):
    with pytest.raises(RecursoNoEncontrado):
        await postular(animal_id="no-existe", adoptante_id="ana", mensaje=MENSAJE)


async def test_regla1_no_se_postula_a_un_animal_adoptado(animales, postulaciones, luna, postular):
    p = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    await AprobarPostulacion(animales, postulaciones).ejecutar(p.id)
    with pytest.raises(AnimalNoDisponible):
        await postular(animal_id=luna.id, adoptante_id="carlos", mensaje=MENSAJE)


async def test_regla2_no_se_duplica_una_postulacion_pendiente(luna, postular):
    await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    with pytest.raises(PostulacionDuplicada):
        await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)


async def test_otro_adoptante_puede_postular_al_mismo_animal(luna, postular):
    await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    otra = await postular(animal_id=luna.id, adoptante_id="carlos", mensaje=MENSAJE)
    assert otra.estado == EstadoPostulacion.PENDIENTE


async def test_se_puede_volver_a_postular_tras_un_rechazo(animales, postulaciones, luna, postular):
    p = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    await RechazarPostulacion(animales, postulaciones).ejecutar(p.id)
    nueva = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    assert nueva.estado == EstadoPostulacion.PENDIENTE


# --- Aprobar (regla 3) -------------------------------------------------------------

async def test_regla3_aprobar_adopta_y_cierra_las_demas(animales, postulaciones, luna, postular):
    de_ana = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    de_carlos = await postular(animal_id=luna.id, adoptante_id="carlos", mensaje=MENSAJE)
    de_vale = await postular(animal_id=luna.id, adoptante_id="vale", mensaje=MENSAJE)

    resultado = await AprobarPostulacion(animales, postulaciones).ejecutar(de_ana.id)

    assert resultado.postulacion.estado == EstadoPostulacion.APROBADA
    assert resultado.animal.estado == EstadoAnimal.ADOPTADO
    assert {p.id for p in resultado.cerradas_automaticamente} == {de_carlos.id, de_vale.id}
    for p_id in (de_carlos.id, de_vale.id):  # también quedó persistido, no solo en el resultado
        guardada = await postulaciones.obtener(p_id)
        assert guardada.estado == EstadoPostulacion.RECHAZADA
        assert guardada.motivo_cierre == MotivoCierre.CIERRE_AUTOMATICO
    assert (await animales.obtener(luna.id)).estado == EstadoAnimal.ADOPTADO


async def test_aprobar_no_toca_postulaciones_de_otros_animales(animales, postulaciones, refugios, luna, postular):
    rocky = await PublicarAnimal(animales, refugios).ejecutar(
        Animal(refugio_id="huellitas", nombre="Rocky", especie="perro", edad_meses=36, sexo="macho")
    )
    a_luna = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    a_rocky = await postular(animal_id=rocky.id, adoptante_id="carlos", mensaje=MENSAJE)

    resultado = await AprobarPostulacion(animales, postulaciones).ejecutar(a_luna.id)

    assert resultado.cerradas_automaticamente == []
    assert (await postulaciones.obtener(a_rocky.id)).esta_pendiente


async def test_no_se_aprueba_una_postulacion_ya_resuelta(animales, postulaciones, luna, postular):
    p = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    await RechazarPostulacion(animales, postulaciones).ejecutar(p.id)
    with pytest.raises(PostulacionYaResuelta):
        await AprobarPostulacion(animales, postulaciones).ejecutar(p.id)


async def test_aprobar_postulacion_inexistente(animales, postulaciones):
    with pytest.raises(RecursoNoEncontrado):
        await AprobarPostulacion(animales, postulaciones).ejecutar("no-existe")


# --- Rechazar ----------------------------------------------------------------------

async def test_rechazar_la_ultima_pendiente_libera_al_animal(animales, postulaciones, luna, postular):
    p = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    resultado = await RechazarPostulacion(animales, postulaciones).ejecutar(p.id)
    assert resultado.postulacion.motivo_cierre == MotivoCierre.RECHAZADA_POR_REFUGIO
    assert resultado.animal.estado == EstadoAnimal.DISPONIBLE


async def test_rechazar_con_otras_pendientes_mantiene_postulado(animales, postulaciones, luna, postular):
    p = await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    await postular(animal_id=luna.id, adoptante_id="carlos", mensaje=MENSAJE)
    resultado = await RechazarPostulacion(animales, postulaciones).ejecutar(p.id)
    assert resultado.animal.estado == EstadoAnimal.POSTULADO


# --- Consultas -----------------------------------------------------------------------

async def test_listar_postulaciones_por_adoptante_y_por_refugio(animales, postulaciones, refugios, luna, postular):
    michi = await PublicarAnimal(animales, refugios).ejecutar(
        Animal(refugio_id="patitas", nombre="Michi", especie="gato", edad_meses=6, sexo="macho")
    )
    await postular(animal_id=luna.id, adoptante_id="ana", mensaje=MENSAJE)
    await postular(animal_id=michi.id, adoptante_id="ana", mensaje=MENSAJE)
    await postular(animal_id=luna.id, adoptante_id="carlos", mensaje=MENSAJE)

    listar = ListarPostulaciones(postulaciones)
    assert len(await listar.por_adoptante("ana")) == 2
    assert len(await listar.por_refugio("huellitas")) == 2
    assert len(await listar.por_refugio("patitas")) == 1
    assert len(await listar.por_refugio("huellitas", EstadoPostulacion.APROBADA)) == 0


# --- Validaciones de existencia -------------------------------------------------------

async def test_publicar_en_refugio_inexistente(animales, refugios):
    animal = Animal(refugio_id="fantasma", nombre="Toby", especie="perro", edad_meses=5, sexo="macho")
    with pytest.raises(RecursoNoEncontrado):
        await PublicarAnimal(animales, refugios).ejecutar(animal)


async def test_postular_con_adoptante_inexistente(luna, postular):
    with pytest.raises(RecursoNoEncontrado):
        await postular(animal_id=luna.id, adoptante_id="fantasma", mensaje=MENSAJE)


# --- Adoptantes -------------------------------------------------------------------------

async def test_registrar_adoptante_nuevo_y_reutilizar_por_email(adoptantes):
    registrar = RegistrarAdoptante(adoptantes).ejecutar
    nuevo = Adoptante(nombre="Sofía", email="Sofia@Mail.com", telefono="3004445566", ciudad="Cali")
    creado, fue_creado = await registrar(nuevo)
    otra_vez, fue_creado_2 = await registrar(nuevo.model_copy(update={"email": "sofia@mail.com"}))
    assert fue_creado and not fue_creado_2
    assert otra_vez.id == creado.id


# --- Flujo end-to-end del README ---------------------------------------------------------

async def test_flujo_completo(animales, postulaciones, refugios, adoptantes):
    # 1. El refugio publica
    rocky = await PublicarAnimal(animales, refugios).ejecutar(
        Animal(refugio_id="huellitas", nombre="Rocky", especie="perro", edad_meses=36, sexo="macho",
               detalles_especie={"raza": "Labrador", "tamano": "grande"})
    )
    # 2-3. Dos adoptantes consultan y postulan; el sistema valida
    postular = Postular(animales, postulaciones, adoptantes).ejecutar
    await ConsultarAnimal(animales).ejecutar(rocky.id)
    de_ana = await postular(animal_id=rocky.id, adoptante_id="ana", mensaje=MENSAJE)
    await postular(animal_id=rocky.id, adoptante_id="carlos", mensaje="Me encantaría darle un hogar.")
    # 4-5. El refugio aprueba a Ana: Rocky adoptado y la de Carlos se cierra sola
    resultado = await AprobarPostulacion(animales, postulaciones).ejecutar(de_ana.id)
    assert resultado.animal.estado == EstadoAnimal.ADOPTADO
    assert len(resultado.cerradas_automaticamente) == 1
    # Ya nadie más puede postular
    with pytest.raises(AnimalNoDisponible):
        await postular(animal_id=rocky.id, adoptante_id="vale", mensaje=MENSAJE)
