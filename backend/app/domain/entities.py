"""Entidades del dominio. Solo dependen de Pydantic y de la librería estándar: no importan
FastAPI, Motor ni nada de application/ o adapters/.

Pydantic garantiza aquí la forma de las entidades (tipos, rangos, enums). Las reglas de negocio
están en los métodos y lanzan excepciones de dominio (ADR-006).
Los IDs son str: el adaptador de Mongo traduce ObjectId <-> str y snake_case <-> contrato API.
"""
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.exceptions import AnimalNoDisponible, PostulacionYaResuelta, TransicionInvalida


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class Especie(StrEnum):
    PERRO = "perro"
    GATO = "gato"
    AVE = "ave"
    OTRO = "otro"


class Sexo(StrEnum):
    MACHO = "macho"
    HEMBRA = "hembra"


class EstadoAnimal(StrEnum):
    DISPONIBLE = "disponible"
    POSTULADO = "postulado"  # tiene al menos una postulación pendiente
    ADOPTADO = "adoptado"


class EstadoPostulacion(StrEnum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


class MotivoCierre(StrEnum):
    RECHAZADA_POR_REFUGIO = "rechazada_por_refugio"
    CIERRE_AUTOMATICO = "cierre_automatico"


class Entidad(BaseModel):
    # validate_assignment: los cambios de estado también se validan, no solo la construcción.
    model_config = ConfigDict(validate_assignment=True)

    id: str | None = None  # None hasta que el repositorio la persiste


# --- Objetos de valor (embebidos en el documento del animal) -----------------

class Salud(BaseModel):
    vacunado: bool = False
    esterilizado: bool = False
    desparasitado: bool = False
    notas: str | None = None


class Foto(BaseModel):
    url: str
    descripcion: str | None = None


class Direccion(BaseModel):
    ciudad: str
    barrio: str | None = None
    linea: str | None = None


# --- Entidades ---------------------------------------------------------------

class Refugio(Entidad):
    nombre: str = Field(min_length=1)
    email: str
    telefono: str | None = None
    direccion: Direccion
    fecha_creacion: datetime = Field(default_factory=_ahora)


class Adoptante(Entidad):
    nombre: str = Field(min_length=1)
    email: str
    telefono: str
    ciudad: str
    fecha_registro: datetime = Field(default_factory=_ahora)


class Animal(Entidad):
    refugio_id: str
    nombre: str = Field(min_length=1, max_length=60)
    especie: Especie
    edad_meses: int = Field(ge=0)
    sexo: Sexo
    estado: EstadoAnimal = EstadoAnimal.DISPONIBLE
    temperamento: list[str] = Field(default_factory=list)
    salud: Salud = Field(default_factory=Salud)
    fotos: list[Foto] = Field(default_factory=list)
    # Campos libres según la especie (perro: tamano; ave: habla...). Es lo que aprovecha Mongo.
    detalles_especie: dict[str, Any] = Field(default_factory=dict)
    fecha_publicacion: datetime = Field(default_factory=_ahora)

    @property
    def texto_adoptado(self) -> str:
        return "adoptada" if self.sexo == Sexo.HEMBRA else "adoptado"

    def puede_recibir_postulaciones(self) -> bool:
        # Se admite postular en "disponible" y en "postulado"; si no, nunca habría dos
        # pendientes y el cierre automático no se ejecutaría (contrato API, sección 5.1).
        return self.estado != EstadoAnimal.ADOPTADO

    def validar_postulable(self) -> None:
        if not self.puede_recibir_postulaciones():
            raise AnimalNoDisponible(f"{self.nombre} ya fue {self.texto_adoptado}.")

    def registrar_postulacion(self) -> None:
        self.validar_postulable()
        self.estado = EstadoAnimal.POSTULADO

    def marcar_adoptado(self) -> None:
        if self.estado != EstadoAnimal.POSTULADO:
            raise TransicionInvalida(f"{self.nombre} no tiene postulaciones para aprobar.")
        self.estado = EstadoAnimal.ADOPTADO

    def liberar(self) -> None:
        """Vuelve a disponible cuando el refugio rechazó todas las pendientes."""
        if self.estado == EstadoAnimal.ADOPTADO:
            raise TransicionInvalida(f"{self.nombre} ya fue {self.texto_adoptado}.")
        self.estado = EstadoAnimal.DISPONIBLE


class Postulacion(Entidad):
    animal_id: str
    adoptante_id: str
    mensaje: str = Field(min_length=10, max_length=500)
    estado: EstadoPostulacion = EstadoPostulacion.PENDIENTE
    motivo_cierre: MotivoCierre | None = None
    fecha_postulacion: datetime = Field(default_factory=_ahora)
    fecha_resolucion: datetime | None = None

    @property
    def esta_pendiente(self) -> bool:
        return self.estado == EstadoPostulacion.PENDIENTE

    def aprobar(self) -> None:
        self._resolver(EstadoPostulacion.APROBADA, motivo=None)

    def rechazar(self, motivo: MotivoCierre = MotivoCierre.RECHAZADA_POR_REFUGIO) -> None:
        self._resolver(EstadoPostulacion.RECHAZADA, motivo)

    def cerrar_automaticamente(self) -> None:
        """Regla 3: otra postulación sobre el mismo animal fue aprobada."""
        self.rechazar(MotivoCierre.CIERRE_AUTOMATICO)

    def _resolver(self, estado: EstadoPostulacion, motivo: MotivoCierre | None) -> None:
        if not self.esta_pendiente:
            raise PostulacionYaResuelta(f"La postulación ya está {self.estado}.")
        self.estado = estado
        self.motivo_cierre = motivo
        self.fecha_resolucion = _ahora()
