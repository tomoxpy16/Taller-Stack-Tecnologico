"""Pruebas de arquitectura: las reglas de dependencia del estilo Hexagonal, verificadas sobre los
imports reales. Son la evidencia de que el diseño evita Tight Coupling, Big Ball of Mud y Fat
Controllers (docs/patrones-antipatrones.md); si alguien rompe una capa, fallan."""
import ast
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"


def imports_de(carpeta: str) -> dict[str, set[str]]:
    resultado = {}
    for archivo in (APP / carpeta).rglob("*.py"):
        modulos = set()
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos.add(nodo.module)
            elif isinstance(nodo, ast.Import):
                modulos.update(alias.name for alias in nodo.names)
        resultado[str(archivo.relative_to(APP))] = modulos
    return resultado


def violaciones(carpeta: str, prohibidos: tuple[str, ...]) -> list[str]:
    return [
        f"{archivo} importa {modulo}"
        for archivo, modulos in imports_de(carpeta).items()
        for modulo in modulos
        if modulo.startswith(prohibidos)
    ]


INFRA = ("fastapi", "starlette", "motor", "pymongo", "bson")


@pytest.mark.parametrize("capa, prohibidos", [
    ("domain", INFRA + ("app.application", "app.adapters")),  # el dominio no conoce a nadie
    ("application", INFRA + ("app.adapters",)),                # la aplicación solo conoce el dominio
])
def test_regla_de_dependencia_hacia_adentro(capa, prohibidos):
    assert violaciones(capa, prohibidos) == []


def test_solo_el_composition_root_conoce_los_adaptadores_de_salida():
    """Los routers piden repositorios a dependencies.py; ninguno instancia un adaptador concreto."""
    culpables = [
        v for v in violaciones("adapters/inbound", ("app.adapters.outbound",))
        if not v.startswith(str(Path("adapters/inbound/api/dependencies.py")))
    ]
    assert culpables == []


def test_los_adaptadores_de_salida_no_conocen_http():
    assert violaciones("adapters/outbound", ("fastapi", "starlette", "app.adapters.inbound")) == []


def test_los_routers_no_contienen_reglas_de_negocio():
    """Fat Controllers: un router traduce HTTP <-> caso de uso. No lanza excepciones de dominio
    ni cambia estados de entidades: eso es del núcleo."""
    for archivo in ("animals.py", "postulaciones.py", "refugios.py", "adoptantes.py"):
        fuente = (APP / "adapters/inbound/api" / archivo).read_text(encoding="utf-8")
        assert "app.domain.exceptions" not in fuente, archivo
        for mutacion in (".aprobar()", ".rechazar(", ".marcar_adoptado()", ".registrar_postulacion()",
                         "existe_pendiente("):
            assert mutacion not in fuente, f"{archivo} contiene {mutacion}"
        assert not re.search(r"\.estado\s*=(?!=)", fuente), f"{archivo} asigna un estado"  # comparar sí


def test_las_entidades_con_reglas_no_son_anemicas():
    """Anemic Domain Model: Animal y Postulacion tienen comportamiento, no solo datos."""
    from app.domain.entities import Animal, Postulacion

    def metodos(cls):
        return {n for n, v in vars(cls).items() if callable(v) and not n.startswith("__")}

    assert {"validar_postulable", "registrar_postulacion", "marcar_adoptado", "liberar"} <= metodos(Animal)
    assert {"aprobar", "rechazar", "cerrar_automaticamente"} <= metodos(Postulacion)
