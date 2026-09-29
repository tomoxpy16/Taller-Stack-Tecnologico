"""Adaptador de salida MongoDB: cumple los puertos de app/application/ports con Motor.

Es el único lugar que conoce cómo se guardan los documentos. Traduce en los dos sentidos:
  - ObjectId <-> str (el dominio y la API solo ven strings).
  - Colección `animales` <-> entidad Animal (el tipo `animals` lo pone el adaptador de entrada).
  - Campos de la semilla que el dominio no modela (`salud.condiciones`, `salud.ultima_revision`)
    se conservan al actualizar, y `condiciones` alimenta `salud.notas` si no hay notas.
  - `motivo_rechazo` (texto libre de la semilla) -> enum `motivo_cierre`.
  - DuplicateKeyError del índice `postulacion_pendiente_unica` -> PostulacionDuplicada (409).
  - DuplicateKeyError del email de adoptante -> se reutiliza el adoptante existente.
"""
import re
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from app.domain.entities import (
    Adoptante,
    Animal,
    Entidad,
    Especie,
    EstadoAnimal,
    EstadoPostulacion,
    MotivoCierre,
    Postulacion,
    Refugio,
)
from app.domain.exceptions import PostulacionDuplicada

# Subdocumentos que se actualizan campo a campo ($set con notación de punto), para no borrar
# lo que la semilla guarda y el dominio no modela.
_SUBDOCUMENTOS_PARCIALES = {"salud", "direccion"}


# --- Traducción de IDs ---------------------------------------------------------

def _ref(valor: str) -> ObjectId | str:
    """Id del dominio -> valor en Mongo: ObjectId si el string lo es; si no, el string tal cual
    (un id que no es ObjectId simplemente no se encuentra, en vez de fallar con InvalidId)."""
    try:
        return ObjectId(valor)
    except (InvalidId, TypeError):
        return valor


def _a_dominio(doc: dict[str, Any], *referencias: str) -> dict[str, Any]:
    """Documento de Mongo -> dict listo para construir la entidad (ids como str)."""
    datos = dict(doc)
    datos["id"] = str(datos.pop("_id"))
    for campo in referencias:
        if datos.get(campo) is not None:
            datos[campo] = str(datos[campo])
    return datos


def _a_documento(entidad: Entidad, *referencias: str) -> dict[str, Any]:
    """Entidad -> documento de Mongo sin `_id` (ids referenciados como ObjectId)."""
    doc = entidad.model_dump(mode="python", exclude={"id"})
    for campo in referencias:
        if doc.get(campo) is not None:
            doc[campo] = _ref(doc[campo])
    return doc


def _set_parcial(doc: dict[str, Any]) -> dict[str, Any]:
    """Aplana los subdocumentos parciales: {"salud": {"vacunado": x}} -> {"salud.vacunado": x}."""
    plano: dict[str, Any] = {}
    for campo, valor in doc.items():
        if campo in _SUBDOCUMENTOS_PARCIALES and isinstance(valor, dict):
            plano.update({f"{campo}.{sub}": v for sub, v in valor.items()})
        else:
            plano[campo] = valor
    return plano


class _RepositorioMongo:
    coleccion: str
    referencias: tuple[str, ...] = ()

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db

    @property
    def _col(self) -> AsyncIOMotorCollection:
        return self._db[self.coleccion]

    async def _buscar_por_id(self, entidad_id: str) -> dict[str, Any] | None:
        return await self._col.find_one({"_id": _ref(entidad_id)})

    async def _guardar(self, entidad: Entidad) -> str:
        """Inserta si la entidad no tiene id; si no, actualiza (o crea con ese id). Devuelve el id."""
        doc = _a_documento(entidad, *self.referencias)
        if entidad.id is None:
            resultado = await self._col.insert_one(doc)
            return str(resultado.inserted_id)
        await self._col.update_one({"_id": _ref(entidad.id)}, {"$set": _set_parcial(doc)}, upsert=True)
        return entidad.id


# --- Animales ------------------------------------------------------------------

def _animal(doc: dict[str, Any]) -> Animal:
    datos = _a_dominio(doc, "refugio_id")
    salud = dict(datos.get("salud") or {})
    if not salud.get("notas") and salud.get("condiciones"):
        salud["notas"] = ", ".join(salud["condiciones"])
    datos["salud"] = salud
    return Animal.model_validate(datos)


class MongoAnimalRepository(_RepositorioMongo):
    coleccion = "animales"
    referencias = ("refugio_id",)

    async def obtener(self, animal_id: str) -> Animal | None:
        doc = await self._buscar_por_id(animal_id)
        return _animal(doc) if doc else None

    async def listar(
        self,
        *,
        estado: EstadoAnimal | None = None,
        especie: Especie | None = None,
        refugio_id: str | None = None,
        pagina: int = 1,
        tamano: int = 12,
    ) -> tuple[list[Animal], int]:
        filtro: dict[str, Any] = {}
        if estado is not None:
            filtro["estado"] = str(estado)
        if especie is not None:
            filtro["especie"] = str(especie)
        if refugio_id is not None:
            filtro["refugio_id"] = _ref(refugio_id)

        total = await self._col.count_documents(filtro)
        cursor = (
            self._col.find(filtro)
            .sort([("fecha_publicacion", DESCENDING), ("_id", DESCENDING)])
            .skip((pagina - 1) * tamano)
            .limit(tamano)
        )
        return [_animal(doc) async for doc in cursor], total

    async def guardar(self, animal: Animal) -> Animal:
        return await self.obtener(await self._guardar(animal))

    async def ids_del_refugio(self, refugio_id: str) -> list[ObjectId | str]:
        return await self._col.distinct("_id", {"refugio_id": _ref(refugio_id)})


# --- Postulaciones -------------------------------------------------------------

def _postulacion(doc: dict[str, Any]) -> Postulacion:
    datos = _a_dominio(doc, "animal_id", "adoptante_id")
    legado = datos.pop("motivo_rechazo", None)
    if datos.get("motivo_cierre") is None and datos.get("estado") == EstadoPostulacion.RECHAZADA:
        # La semilla original guarda un texto libre; se traduce al enum del contrato.
        automatico = legado and "autom" in legado.lower()
        datos["motivo_cierre"] = (
            MotivoCierre.CIERRE_AUTOMATICO if automatico else MotivoCierre.RECHAZADA_POR_REFUGIO
        )
    return Postulacion.model_validate(datos)


class MongoPostulacionRepository(_RepositorioMongo):
    coleccion = "postulaciones"
    referencias = ("animal_id", "adoptante_id")

    def __init__(self, db: AsyncIOMotorDatabase, animales: MongoAnimalRepository):
        super().__init__(db)
        # Para filtrar por refugio hay que pasar por los animales (la postulación no guarda el refugio).
        self._animales = animales

    async def _listar(self, filtro: dict[str, Any]) -> list[Postulacion]:
        cursor = self._col.find(filtro).sort([("fecha_postulacion", DESCENDING), ("_id", DESCENDING)])
        return [_postulacion(doc) async for doc in cursor]

    async def obtener(self, postulacion_id: str) -> Postulacion | None:
        doc = await self._buscar_por_id(postulacion_id)
        return _postulacion(doc) if doc else None

    async def listar_por_animal(
        self, animal_id: str, *, estado: EstadoPostulacion | None = None
    ) -> list[Postulacion]:
        filtro: dict[str, Any] = {"animal_id": _ref(animal_id)}
        if estado is not None:
            filtro["estado"] = str(estado)
        return await self._listar(filtro)

    async def listar_por_adoptante(self, adoptante_id: str) -> list[Postulacion]:
        return await self._listar({"adoptante_id": _ref(adoptante_id)})

    async def listar_por_refugio(self, refugio_id: str) -> list[Postulacion]:
        animales = await self._animales.ids_del_refugio(refugio_id)
        return await self._listar({"animal_id": {"$in": animales}}) if animales else []

    async def existe_pendiente(self, adoptante_id: str, animal_id: str) -> bool:
        filtro = {
            "adoptante_id": _ref(adoptante_id),
            "animal_id": _ref(animal_id),
            "estado": EstadoPostulacion.PENDIENTE.value,
        }
        return await self._col.count_documents(filtro, limit=1) > 0

    async def guardar(self, postulacion: Postulacion) -> Postulacion:
        try:
            postulacion_id = await self._guardar(postulacion)
        except DuplicateKeyError as error:
            # Dos postulaciones simultáneas pasaron existe_pendiente(); el índice único parcial
            # detiene la segunda y aquí se convierte en la misma regla de negocio (409, no 500).
            raise PostulacionDuplicada(
                "Ya tienes una postulación pendiente para este animal."
            ) from error
        return await self.obtener(postulacion_id)


# --- Refugios ------------------------------------------------------------------

class MongoRefugioRepository(_RepositorioMongo):
    coleccion = "refugios"

    async def obtener(self, refugio_id: str) -> Refugio | None:
        doc = await self._buscar_por_id(refugio_id)
        return Refugio.model_validate(_a_dominio(doc)) if doc else None

    async def listar(self) -> list[Refugio]:
        cursor = self._col.find().sort("nombre", ASCENDING)
        return [Refugio.model_validate(_a_dominio(doc)) async for doc in cursor]


# --- Adoptantes ----------------------------------------------------------------

class MongoAdoptanteRepository(_RepositorioMongo):
    coleccion = "adoptantes"

    async def obtener(self, adoptante_id: str) -> Adoptante | None:
        doc = await self._buscar_por_id(adoptante_id)
        return Adoptante.model_validate(_a_dominio(doc)) if doc else None

    async def obtener_por_email(self, email: str) -> Adoptante | None:
        # Sin distinguir mayúsculas; re.escape evita que un email se interprete como regex.
        filtro = {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
        doc = await self._col.find_one(filtro)
        return Adoptante.model_validate(_a_dominio(doc)) if doc else None

    async def guardar(self, adoptante: Adoptante) -> Adoptante:
        try:
            return await self.obtener(await self._guardar(adoptante))
        except DuplicateKeyError:
            # Dos registros simultáneos con el mismo email pasaron obtener_por_email(); el índice
            # único detiene el segundo y se reutiliza el adoptante existente (contrato 5.3), no 500.
            existente = await self.obtener_por_email(adoptante.email)
            if existente is None or adoptante.id is not None:  # solo aplica al registro (insert)
                raise
            return existente
