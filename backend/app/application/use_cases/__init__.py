from app.application.use_cases.adoptantes import ConsultarAdoptante, RegistrarAdoptante
from app.application.use_cases.animales import ConsultarAnimal, ListarAnimales, PublicarAnimal
from app.application.use_cases.postulaciones import (
    AprobarPostulacion,
    ListarPostulaciones,
    Postular,
    RechazarPostulacion,
    ResultadoResolucion,
)
from app.application.use_cases.refugios import ConsultarRefugio, ListarRefugios

__all__ = [
    "AprobarPostulacion",
    "ConsultarAdoptante",
    "ConsultarAnimal",
    "ConsultarRefugio",
    "ListarAnimales",
    "ListarPostulaciones",
    "ListarRefugios",
    "Postular",
    "PublicarAnimal",
    "RechazarPostulacion",
    "RegistrarAdoptante",
    "ResultadoResolucion",
]
