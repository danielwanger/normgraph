"""Normgraph API — semantische Suche + Verweis-Navigation über deutsches Bundesrecht."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import close_pool, init_pool
from app.routers.norms import router as norms_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="Normgraph API",
    description="Semantische Suche und Verweis-Navigation über deutsches Bundesrecht.",
    version="0.1.0",
    lifespan=lifespan,
)

# Für die lokale Frontend-Entwicklung offen; vor Deployment auf konkrete Origin(s) einschränken.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(norms_router)


@app.get("/health")
def health():
    return {"status": "ok"}