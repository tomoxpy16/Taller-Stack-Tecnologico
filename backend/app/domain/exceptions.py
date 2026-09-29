class ErrorDeDominio(Exception):
    """Base de las violaciones de reglas de negocio. El dominio no conoce HTTP: el adaptador
    de entrada traduce cada subclase a su código JSON:API (ver docs/contrato-api-jsonapi.md)."""


class AnimalNoDisponible(ErrorDeDominio):
    """Regla 1: no se puede postular a un animal que ya fue adoptado."""


class PostulacionDuplicada(ErrorDeDominio):
    """Regla 2: el adoptante ya tiene una postulación pendiente sobre el mismo animal."""


class PostulacionYaResuelta(ErrorDeDominio):
    """Solo una postulación pendiente puede aprobarse o rechazarse."""


class TransicionInvalida(ErrorDeDominio):
    """Cambio de estado del animal que el ciclo de vida no permite."""
