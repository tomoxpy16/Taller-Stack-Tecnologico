"""Adaptador de entrada REST / JSON:API. Se monta en /v1 (Nginx quita el prefijo /api)."""
from fastapi import APIRouter

from app.adapters.inbound.api import adoptantes, animals, postulaciones, refugios

router = APIRouter(prefix="/v1")
for modulo in (animals, postulaciones, refugios, adoptantes):
    router.include_router(modulo.router)
