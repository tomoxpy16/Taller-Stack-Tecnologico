"""Documentos JSON:API de entrada. Pydantic valida aquí solo FORMATO y tipos, en el borde;
las reglas de negocio las valida el dominio (ADR-006). Cada modelo sabe convertirse a entidad."""
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, create_model
from pydantic.alias_generators import to_camel

from app.domain.entities import Adoptante, Animal, Especie, Foto, Salud, Sexo

Texto = Annotated[str, StringConstraints(strip_whitespace=True)]
# Solo URLs http(s) o imágenes embebidas: evita guardar "javascript:..." que luego se pinta en <img src>.
UrlFoto = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2_000_000,
                                           pattern=r"^(https?://\S+|data:image/[\w.+-]+[;,]\S*)$")]


class _Modelo(BaseModel):
    # Atributos en camelCase como el contrato; se ignora lo desconocido o de solo lectura (estado...).
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


def _relacion(tipo: str, nombre: str) -> type[BaseModel]:
    """Relación to-one {"data": {"type": <tipo>, "id": ...}}; un `type` distinto es 400."""
    ref = create_model(
        f"Ref{nombre}",
        type=(Literal[tipo], ...),  # type: ignore[valid-type]
        id=(Annotated[str, StringConstraints(min_length=1)], ...),
    )
    return create_model(f"Rel{nombre}", data=(ref, ...))


RelRefugio = _relacion("refugios", "Refugio")
RelAnimal = _relacion("animals", "Animal")
RelAdoptante = _relacion("adoptantes", "Adoptante")


# --- animals ------------------------------------------------------------------

class FotoEntrada(BaseModel):
    url: UrlFoto
    descripcion: str | None = None


class SaludEntrada(_Modelo):
    vacunado: bool = False
    esterilizado: bool = False
    desparasitado: bool = False
    notas: str | None = None


class AnimalAtributos(_Modelo):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    especie: Especie
    edad_meses: int = Field(ge=0)
    sexo: Sexo
    # Topes de tamaño: sin ellos un cliente podría guardar documentos arbitrariamente grandes.
    temperamento: list[Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)]] = Field(
        default_factory=list, max_length=15)
    salud: SaludEntrada = Field(default_factory=SaludEntrada)
    fotos: list[UrlFoto | FotoEntrada] = Field(default_factory=list, max_length=10)  # contrato: URLs
    detalles_especie: dict[str, Any] = Field(default_factory=dict, max_length=20)


class AnimalRelaciones(BaseModel):
    refugio: RelRefugio


class AnimalCrearData(BaseModel):
    type: Literal["animals"]
    attributes: AnimalAtributos
    relationships: AnimalRelaciones


class AnimalCrear(BaseModel):
    data: AnimalCrearData

    def a_entidad(self) -> Animal:
        a = self.data.attributes
        return Animal(
            refugio_id=self.data.relationships.refugio.data.id,
            nombre=a.nombre,
            especie=a.especie,
            edad_meses=a.edad_meses,
            sexo=a.sexo,
            temperamento=[t for t in a.temperamento if t],
            salud=Salud(**a.salud.model_dump()),
            fotos=[Foto(url=f) if isinstance(f, str) else Foto(**f.model_dump()) for f in a.fotos],
            detalles_especie=a.detalles_especie,
        )


# --- adoptantes -----------------------------------------------------------------

class AdoptanteAtributos(_Modelo):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    email: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")]
    telefono: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{7,13}$")]
    ciudad: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2)]


class AdoptanteCrearData(BaseModel):
    type: Literal["adoptantes"]
    attributes: AdoptanteAtributos


class AdoptanteCrear(BaseModel):
    data: AdoptanteCrearData

    def a_entidad(self) -> Adoptante:
        return Adoptante(**self.data.attributes.model_dump())


# --- postulaciones ----------------------------------------------------------------

class PostulacionAtributos(_Modelo):
    mensaje: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=500)]


class PostulacionRelaciones(BaseModel):
    animal: RelAnimal
    adoptante: RelAdoptante


class PostulacionCrearData(BaseModel):
    type: Literal["postulaciones"]
    attributes: PostulacionAtributos
    relationships: PostulacionRelaciones


class PostulacionCrear(BaseModel):
    data: PostulacionCrearData


class PostulacionResolverAtributos(_Modelo):
    estado: Literal["aprobada", "rechazada"]


class PostulacionResolverData(BaseModel):
    type: Literal["postulaciones"]
    id: str
    attributes: PostulacionResolverAtributos


class PostulacionResolver(BaseModel):
    data: PostulacionResolverData
