"""Casos de uso probados con MOCKS de los puertos (SCRUM-15, evidencia de testabilidad).

A diferencia de test_use_cases.py (adaptador in-memory, que verifica el resultado), aquí cada
puerto es un AsyncMock con la forma exacta del Protocol y se verifica la INTERACCIÓN: qué métodos
del puerto llama el caso de uso, con qué argumentos, en qué orden, y cuáles no llama nunca.
No hay base de datos, ni servidor, ni red: solo el núcleo de la aplicación.
"""
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.application.ports import (
    AdoptanteRepository,
    AnimalRepository,
    PostulacionRepository,
    RefugioRepository,
)
from app.application.use_cases import (
    AprobarPostulacion,
    Postular,
    ConsultarAdoptante,
    ConsultarRefugio,
    ListarRefugios,
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
    Postulacion,
    Refugio,
)
from app.domain.exceptions import (
    AnimalNoDisponible,
    PostulacionDuplicada,
    PostulacionYaResuelta,
    RecursoNoEncontrado,
    TransicionInvalida,
)

MENSAJE = "Tengo patio grande y experiencia con perros."


def mock_de(puerto):
    """Mock que solo acepta los métodos que declara el puerto: si el caso de uso llamara algo
    que no está en el contrato, la prueba falla con AttributeError."""
    return AsyncMock(spec=puerto)


def guarda_lo_que_recibe(mock_guardar, prefijo="id"):
    """Simula al repositorio: devuelve la entidad recibida, con id si no lo tenía."""
    async def guardar(entidad):
        return entidad if entidad.id else entidad.model_copy(update={"id": f"{prefijo}-nuevo"})
    mock_guardar.side_effect = guardar


def animal(estado=EstadoAnimal.DISPONIBLE, **cambios):
    return Animal(id="luna", refugio_id="huellitas", nombre="Luna", especie="perro",
                  edad_meses=24, sexo="hembra", estado=estado, **cambios)


def postulacion(id_, adoptante="ana", estado=EstadoPostulacion.PENDIENTE):
    return Postulacion(id=id_, animal_id="luna", adoptante_id=adoptante, mensaje=MENSAJE, estado=estado)


@pytest.fixture
def animales():
    m = mock_de(AnimalRepository)
    guarda_lo_que_recibe(m.guardar, "animal")
    return m


@pytest.fixture
def postulaciones():
    m = mock_de(PostulacionRepository)
    guarda_lo_que_recibe(m.guardar, "postulacion")
    m.existe_pendiente.return_value = False
    return m


@pytest.fixture
def adoptantes():
    m = mock_de(AdoptanteRepository)
    m.obtener.return_value = Adoptante(id="ana", nombre="Ana", email="ana@mail.com",
                                       telefono="3001112233", ciudad="Bogotá")
    return m


def test_los_mocks_respetan_el_contrato_del_puerto(animales):
    assert isinstance(animales, AnimalRepository)
    with pytest.raises(AttributeError):
        animales.borrar_todo  # no existe en el puerto


# --- Postular -------------------------------------------------------------------------------

async def test_postular_consulta_valida_y_guarda(animales, postulaciones, adoptantes):
    animales.obtener.return_value = animal()

    creada = await Postular(animales, postulaciones, adoptantes).ejecutar(
        animal_id="luna", adoptante_id="ana", mensaje=MENSAJE)

    animales.obtener.assert_awaited_once_with("luna")
    adoptantes.obtener.assert_awaited_once_with("ana")
    postulaciones.existe_pendiente.assert_awaited_once_with("ana", "luna")
    postulaciones.guardar.assert_awaited_once()
    assert creada.estado == EstadoPostulacion.PENDIENTE
    animal_guardado = animales.guardar.await_args.args[0]
    assert animal_guardado.estado == EstadoAnimal.POSTULADO


async def test_regla1_animal_adoptado_no_escribe_nada(animales, postulaciones, adoptantes):
    animales.obtener.return_value = animal(EstadoAnimal.ADOPTADO)

    with pytest.raises(AnimalNoDisponible):
        await Postular(animales, postulaciones, adoptantes).ejecutar(
            animal_id="luna", adoptante_id="ana", mensaje=MENSAJE)

    postulaciones.existe_pendiente.assert_not_awaited()  # la regla 1 corta antes
    postulaciones.guardar.assert_not_awaited()
    animales.guardar.assert_not_awaited()


async def test_regla2_duplicada_no_escribe_nada(animales, postulaciones, adoptantes):
    animales.obtener.return_value = animal(EstadoAnimal.POSTULADO)
    postulaciones.existe_pendiente.return_value = True

    with pytest.raises(PostulacionDuplicada):
        await Postular(animales, postulaciones, adoptantes).ejecutar(
            animal_id="luna", adoptante_id="ana", mensaje=MENSAJE)

    postulaciones.guardar.assert_not_awaited()
    animales.guardar.assert_not_awaited()


async def test_postular_a_animal_inexistente_no_consulta_nada_mas(animales, postulaciones, adoptantes):
    animales.obtener.return_value = None

    with pytest.raises(RecursoNoEncontrado):
        await Postular(animales, postulaciones, adoptantes).ejecutar(
            animal_id="fantasma", adoptante_id="ana", mensaje=MENSAJE)

    adoptantes.obtener.assert_not_awaited()
    postulaciones.existe_pendiente.assert_not_awaited()


# --- Aprobar (regla 3: cierre automático) ---------------------------------------------------

async def test_aprobar_guarda_la_adopcion_antes_de_cerrar_las_demas(animales, postulaciones):
    aprobada, otra_1, otra_2 = postulacion("p1"), postulacion("p2", "carlos"), postulacion("p3", "vale")
    postulaciones.obtener.return_value = aprobada
    animales.obtener.return_value = animal(EstadoAnimal.POSTULADO)
    postulaciones.listar_por_animal.return_value = [otra_1, otra_2]
    # Un "gestor" común registra el orden de TODAS las llamadas a ambos puertos.
    gestor = MagicMock()
    gestor.attach_mock(animales.guardar, "animales_guardar")
    gestor.attach_mock(postulaciones.guardar, "postulaciones_guardar")

    resultado = await AprobarPostulacion(animales, postulaciones).ejecutar("p1")

    orden = [(c[0], c.args[0].id) for c in gestor.mock_calls]
    assert orden == [
        ("animales_guardar", "luna"),     # 1. el animal queda adoptado
        ("postulaciones_guardar", "p1"),  # 2. la aprobación
        ("postulaciones_guardar", "p2"),  # 3. cierre automático de las demás
        ("postulaciones_guardar", "p3"),
    ]
    postulaciones.listar_por_animal.assert_awaited_once_with("luna", estado=EstadoPostulacion.PENDIENTE)
    assert resultado.animal.estado == EstadoAnimal.ADOPTADO
    assert all(p.motivo_cierre == MotivoCierre.CIERRE_AUTOMATICO for p in resultado.cerradas_automaticamente)


async def test_aprobar_una_resuelta_no_escribe_nada(animales, postulaciones):
    postulaciones.obtener.return_value = postulacion("p1", estado=EstadoPostulacion.RECHAZADA)
    animales.obtener.return_value = animal(EstadoAnimal.POSTULADO)

    with pytest.raises(PostulacionYaResuelta):
        await AprobarPostulacion(animales, postulaciones).ejecutar("p1")

    animales.guardar.assert_not_awaited()
    postulaciones.guardar.assert_not_awaited()
    postulaciones.listar_por_animal.assert_not_awaited()


# --- Rechazar -------------------------------------------------------------------------------

async def test_rechazar_con_otras_pendientes_no_toca_al_animal(animales, postulaciones):
    postulaciones.obtener.return_value = postulacion("p1")
    animales.obtener.return_value = animal(EstadoAnimal.POSTULADO)
    postulaciones.listar_por_animal.return_value = [postulacion("p2", "carlos")]

    resultado = await RechazarPostulacion(animales, postulaciones).ejecutar("p1")

    assert resultado.postulacion.motivo_cierre == MotivoCierre.RECHAZADA_POR_REFUGIO
    animales.guardar.assert_not_awaited()
    assert postulaciones.guardar.await_count == 1  # solo la rechazada; las demás no se cierran


async def test_rechazar_la_ultima_pendiente_libera_al_animal(animales, postulaciones):
    postulaciones.obtener.return_value = postulacion("p1")
    animales.obtener.return_value = animal(EstadoAnimal.POSTULADO)
    postulaciones.listar_por_animal.return_value = []

    await RechazarPostulacion(animales, postulaciones).ejecutar("p1")

    assert animales.guardar.await_args.args[0].estado == EstadoAnimal.DISPONIBLE


# --- Publicar y registrar -------------------------------------------------------------------

async def test_publicar_en_refugio_inexistente_no_guarda(animales):
    refugios = mock_de(RefugioRepository)
    refugios.obtener.return_value = None

    with pytest.raises(RecursoNoEncontrado):
        await PublicarAnimal(animales, refugios).ejecutar(animal())

    animales.guardar.assert_not_awaited()


async def test_publicar_ignora_el_estado_y_el_id_del_cliente(animales):
    refugios = mock_de(RefugioRepository)
    refugios.obtener.return_value = Refugio(id="huellitas", nombre="H", email="h@h.org",
                                            direccion=Direccion(ciudad="Bogotá"))

    await PublicarAnimal(animales, refugios).ejecutar(animal(EstadoAnimal.ADOPTADO))

    guardado = animales.guardar.await_args.args[0]
    assert guardado.id is None and guardado.estado == EstadoAnimal.DISPONIBLE


async def test_registrar_con_email_existente_no_crea_otro():
    adoptantes = mock_de(AdoptanteRepository)
    existente = Adoptante(id="ana", nombre="Ana", email="ana@mail.com", telefono="3001112233", ciudad="Bogotá")
    adoptantes.obtener_por_email.return_value = existente

    adoptante, creado = await RegistrarAdoptante(adoptantes).ejecutar(existente.model_copy(update={"id": None}))

    assert (adoptante.id, creado) == ("ana", False)
    assert adoptantes.mock_calls == [call.obtener_por_email("ana@mail.com")]  # nada más


# --- Consultas -------------------------------------------------------------------------------

async def test_consultas_de_refugio_delegan_en_el_puerto():
    refugios = mock_de(RefugioRepository)
    huellitas = Refugio(id="huellitas", nombre="H", email="h@h.org", direccion=Direccion(ciudad="Bogotá"))
    refugios.listar.return_value = [huellitas]
    refugios.obtener.return_value = huellitas

    assert await ListarRefugios(refugios).ejecutar() == [huellitas]
    assert await ConsultarRefugio(refugios).ejecutar("huellitas") == huellitas
    refugios.obtener.return_value = None
    with pytest.raises(RecursoNoEncontrado):
        await ConsultarRefugio(refugios).ejecutar("fantasma")


async def test_consultar_adoptante(adoptantes):
    assert (await ConsultarAdoptante(adoptantes).ejecutar("ana")).id == "ana"
    adoptantes.obtener.return_value = None
    with pytest.raises(RecursoNoEncontrado):
        await ConsultarAdoptante(adoptantes).ejecutar("fantasma")


async def test_registrar_adoptante_nuevo_lo_guarda():
    adoptantes = mock_de(AdoptanteRepository)
    adoptantes.obtener_por_email.return_value = None
    guarda_lo_que_recibe(adoptantes.guardar, "adoptante")
    nuevo = Adoptante(nombre="Sofía", email="sofia@mail.com", telefono="3004445566", ciudad="Cali")

    adoptante, creado = await RegistrarAdoptante(adoptantes).ejecutar(nuevo)

    assert creado and adoptante.id == "adoptante-nuevo"
    adoptantes.guardar.assert_awaited_once()


def test_un_animal_adoptado_no_se_puede_liberar():
    with pytest.raises(TransicionInvalida):
        animal(EstadoAnimal.ADOPTADO).liberar()
