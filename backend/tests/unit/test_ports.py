"""Los puertos son Protocol: cualquier clase con los mismos métodos los cumple sin heredar.
Estos fakes mínimos lo demuestran; el adaptador in-memory real vive en adapters/."""
from app.application.ports import AnimalRepository, PostulacionRepository
from app.domain.entities import Animal, Postulacion


class AnimalesFalsos:
    async def obtener(self, animal_id): return None
    async def listar(self, **filtros): return [], 0
    async def guardar(self, animal: Animal): return animal


class PostulacionesFalsas:
    async def obtener(self, postulacion_id): return None
    async def listar_por_animal(self, animal_id, *, estado=None): return []
    async def listar_por_adoptante(self, adoptante_id): return []
    async def listar_por_refugio(self, refugio_id): return []
    async def existe_pendiente(self, adoptante_id, animal_id): return False
    async def guardar(self, postulacion: Postulacion): return postulacion


def test_una_clase_con_los_metodos_cumple_el_puerto_sin_heredar():
    assert isinstance(AnimalesFalsos(), AnimalRepository)
    assert isinstance(PostulacionesFalsas(), PostulacionRepository)


def test_una_clase_incompleta_no_cumple_el_puerto():
    assert not isinstance(AnimalesFalsos(), PostulacionRepository)


def test_el_dominio_no_importa_infraestructura():
    import ast
    from pathlib import Path

    import app.domain as dominio

    prohibidos = ("fastapi", "motor", "pymongo", "bson", "app.adapters", "app.application")
    for archivo in Path(dominio.__file__).parent.glob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom):
                modulos = [nodo.module or ""]
            elif isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            else:
                continue
            for modulo in modulos:
                assert not modulo.startswith(prohibidos), f"{archivo.name} importa {modulo}"
