"""Integración del adaptador de salida MongoDB: los repositorios reales contra una base desechable.
Cubren el cumplimiento de los puertos, las traducciones (ObjectId, semilla) y el respaldo del
índice único parcial. Se omiten si Mongo no está arriba (docker compose up -d mongodb)."""
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.adapters.inbound.api.dependencies import crear_repositorios_mongo
from app.application.ports import (
    AdoptanteRepository,
    AnimalRepository,
    PostulacionRepository,
    RefugioRepository,
)
from app.domain.entities import (
    Adoptante,
    Animal,
    Direccion,
    EstadoAnimal,
    EstadoPostulacion,
    MotivoCierre,
    Postulacion,
    Refugio,
)
from app.domain.exceptions import PostulacionDuplicada

pytestmark = pytest.mark.integration

MENSAJE = "Tengo casa con patio y experiencia con perros."


@pytest.fixture
def repos(mongo_db):
    return crear_repositorios_mongo(mongo_db)


async def _insertar_refugio(repos, nombre, email) -> Refugio:
    # RefugioRepository no tiene guardar() (los refugios vienen de la semilla): se insertan directo.
    resultado = await repos.refugios._col.insert_one(
        {"nombre": nombre, "email": email, "direccion": {"ciudad": "Bogotá"}}
    )
    return await repos.refugios.obtener(str(resultado.inserted_id))


async def _animal(repos, refugio_id, **datos) -> Animal:
    base = {"refugio_id": refugio_id, "nombre": "Luna", "especie": "perro", "edad_meses": 24, "sexo": "hembra"}
    return await repos.animales.guardar(Animal(**(base | datos)))


async def _adoptante(repos, email="ana@mail.com") -> Adoptante:
    return await repos.adoptantes.guardar(
        Adoptante(nombre="Ana Gómez", email=email, telefono="3001112233", ciudad="Bogotá")
    )


# --- puertos -----------------------------------------------------------------------------

def test_los_repositorios_mongo_cumplen_los_puertos(repos):
    assert isinstance(repos.animales, AnimalRepository)
    assert isinstance(repos.postulaciones, PostulacionRepository)
    assert isinstance(repos.refugios, RefugioRepository)
    assert isinstance(repos.adoptantes, AdoptanteRepository)


# --- animales ----------------------------------------------------------------------------

async def test_guardar_animal_asigna_id_y_guarda_referencias_como_objectid(repos, mongo_db):
    refugio = await _insertar_refugio(repos, "Huellitas", "h@h.org")
    animal = await _animal(repos, refugio.id, detalles_especie={"tamano": "mediano"})

    assert ObjectId.is_valid(animal.id)
    doc = await mongo_db.animales.find_one({"_id": ObjectId(animal.id)})
    assert doc["refugio_id"] == ObjectId(refugio.id)
    assert doc["estado"] == "disponible"
    assert (await repos.animales.obtener(animal.id)).detalles_especie == {"tamano": "mediano"}


async def test_obtener_con_id_inexistente_o_invalido_devuelve_none(repos):
    assert await repos.animales.obtener(str(ObjectId())) is None
    assert await repos.animales.obtener("no-es-un-objectid") is None
    assert await repos.postulaciones.obtener("nada") is None
    assert await repos.refugios.obtener("nada") is None
    assert await repos.adoptantes.obtener("nada") is None


async def test_listar_animales_filtra_pagina_y_ordena_por_publicacion(repos):
    huellitas = await _insertar_refugio(repos, "Huellitas", "h@h.org")
    patitas = await _insertar_refugio(repos, "Patitas", "p@p.org")
    ahora = datetime.now(timezone.utc)
    await _animal(repos, huellitas.id, nombre="Viejo", fecha_publicacion=ahora - timedelta(days=5))
    await _animal(repos, huellitas.id, nombre="Nuevo", fecha_publicacion=ahora)
    await _animal(repos, patitas.id, nombre="Michi", especie="gato", sexo="macho")

    todos, total = await repos.animales.listar()
    assert total == 3
    pagina, total = await repos.animales.listar(refugio_id=huellitas.id, pagina=1, tamano=1)
    assert total == 2 and [a.nombre for a in pagina] == ["Nuevo"]
    pagina2, _ = await repos.animales.listar(refugio_id=huellitas.id, pagina=2, tamano=1)
    assert [a.nombre for a in pagina2] == ["Viejo"]
    gatos, total = await repos.animales.listar(especie="gato")
    assert total == 1 and gatos[0].nombre == "Michi"
    _, total = await repos.animales.listar(estado=EstadoAnimal.ADOPTADO)
    assert total == 0


async def test_actualizar_animal_no_borra_campos_de_la_semilla(repos, mongo_db):
    """La semilla guarda salud.condiciones y salud.ultima_revision, que el dominio no modela."""
    refugio = await _insertar_refugio(repos, "Huellitas", "h@h.org")
    revision = datetime(2026, 9, 1, tzinfo=timezone.utc)
    resultado = await mongo_db.animales.insert_one({
        "refugio_id": ObjectId(refugio.id), "nombre": "Rocky", "especie": "perro", "edad_meses": 60,
        "sexo": "macho", "estado": "disponible", "temperamento": ["leal"],
        "salud": {"vacunado": True, "esterilizado": True, "desparasitado": True,
                  "condiciones": ["displasia de cadera leve"], "ultima_revision": revision},
        "fotos": [{"url": "https://picsum.photos/seed/rocky1/600/400", "descripcion": "Rocky"}],
        "detalles_especie": {"raza": "Labrador"}, "fecha_publicacion": revision,
    })

    rocky = await repos.animales.obtener(str(resultado.inserted_id))
    assert rocky.salud.notas == "displasia de cadera leve"  # condiciones -> notas
    assert rocky.fotos[0].descripcion == "Rocky"

    rocky.registrar_postulacion()
    await repos.animales.guardar(rocky)

    doc = await mongo_db.animales.find_one({"_id": resultado.inserted_id})
    assert doc["estado"] == "postulado"
    assert doc["salud"]["condiciones"] == ["displasia de cadera leve"]
    assert doc["salud"]["ultima_revision"] is not None


# --- postulaciones ----------------------------------------------------------------------

async def test_postulaciones_por_animal_adoptante_y_refugio(repos):
    huellitas = await _insertar_refugio(repos, "Huellitas", "h@h.org")
    patitas = await _insertar_refugio(repos, "Patitas", "p@p.org")
    luna = await _animal(repos, huellitas.id)
    michi = await _animal(repos, patitas.id, nombre="Michi", especie="gato", sexo="macho")
    ana = await _adoptante(repos)

    p1 = await repos.postulaciones.guardar(Postulacion(animal_id=luna.id, adoptante_id=ana.id, mensaje=MENSAJE))
    await repos.postulaciones.guardar(Postulacion(animal_id=michi.id, adoptante_id=ana.id, mensaje=MENSAJE))

    assert ObjectId.is_valid(p1.id) and p1.animal_id == luna.id and p1.adoptante_id == ana.id
    assert [p.id for p in await repos.postulaciones.listar_por_animal(luna.id)] == [p1.id]
    assert len(await repos.postulaciones.listar_por_adoptante(ana.id)) == 2
    assert [p.animal_id for p in await repos.postulaciones.listar_por_refugio(huellitas.id)] == [luna.id]
    assert await repos.postulaciones.listar_por_refugio(str(ObjectId())) == []
    assert await repos.postulaciones.existe_pendiente(ana.id, luna.id)

    p1.rechazar()
    await repos.postulaciones.guardar(p1)
    assert not await repos.postulaciones.existe_pendiente(ana.id, luna.id)
    pendientes = await repos.postulaciones.listar_por_animal(luna.id, estado=EstadoPostulacion.PENDIENTE)
    assert pendientes == []
    guardada = await repos.postulaciones.obtener(p1.id)
    assert guardada.motivo_cierre == MotivoCierre.RECHAZADA_POR_REFUGIO
    assert guardada.fecha_resolucion is not None


async def test_postulacion_duplicada_simultanea_es_error_de_dominio(repos):
    """Si dos peticiones pasan existe_pendiente() a la vez, el índice único detiene la segunda."""
    refugio = await _insertar_refugio(repos, "Huellitas", "h@h.org")
    luna = await _animal(repos, refugio.id)
    ana = await _adoptante(repos)

    await repos.postulaciones.guardar(Postulacion(animal_id=luna.id, adoptante_id=ana.id, mensaje=MENSAJE))
    with pytest.raises(PostulacionDuplicada):
        await repos.postulaciones.guardar(Postulacion(animal_id=luna.id, adoptante_id=ana.id, mensaje=MENSAJE))


async def test_motivo_rechazo_de_la_semilla_se_traduce_al_enum(repos, mongo_db):
    resultado = await mongo_db.postulaciones.insert_one({
        "adoptante_id": ObjectId(), "animal_id": ObjectId(), "estado": "rechazada",
        "mensaje": "Me gustan mucho los gatos siameses.",
        "fecha_postulacion": datetime.now(timezone.utc), "fecha_resolucion": datetime.now(timezone.utc),
        "motivo_rechazo": "Cerrada automáticamente: el animal fue adoptado",
    })
    postulacion = await repos.postulaciones.obtener(str(resultado.inserted_id))
    assert postulacion.motivo_cierre == MotivoCierre.CIERRE_AUTOMATICO


# --- refugios y adoptantes ---------------------------------------------------------------

async def test_refugios_ordenados_por_nombre(repos):
    await _insertar_refugio(repos, "Patitas Felices", "p@p.org")
    await _insertar_refugio(repos, "Fundación Huellitas", "h@h.org")
    assert [r.nombre for r in await repos.refugios.listar()] == ["Fundación Huellitas", "Patitas Felices"]
    assert isinstance((await repos.refugios.listar())[0].direccion, Direccion)


async def test_adoptante_por_email_sin_distinguir_mayusculas(repos):
    ana = await _adoptante(repos, email="Ana.Gomez@mail.com")
    assert (await repos.adoptantes.obtener_por_email("ana.gomez@MAIL.com")).id == ana.id
    assert await repos.adoptantes.obtener_por_email("ana.gomez@mail.co") is None
    assert await repos.adoptantes.obtener_por_email("ana.gomez@mail.com.*") is None  # no es regex


async def test_registro_simultaneo_con_el_mismo_email_reutiliza_el_adoptante(repos):
    """Si dos registros pasan obtener_por_email() a la vez, el segundo no falla: reutiliza el primero."""
    ana = await _adoptante(repos, email="ana@mail.com")
    otra = await _adoptante(repos, email="ana@mail.com")
    assert otra.id == ana.id
