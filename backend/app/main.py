from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.adapters.outbound.persistence.mongo import client as mongo
from app.adapters.outbound.persistence.mongo.indexes import ensure_indexes


@asynccontextmanager
async def lifespan(_: FastAPI):
    mongo.connect()
    await ensure_indexes(mongo.get_database())
    yield
    mongo.close()


app = FastAPI(title="Plataforma de Adopción de Mascotas", lifespan=lifespan)


@app.get("/health", tags=["infra"])
async def health():
    try:
        await mongo.get_database().command("ping")
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "mongodb": "down"})
    return {"status": "ok", "mongodb": "up"}


# Los routers de animals, postulaciones y refugios (app/adapters/inbound/api) se registran aquí.
