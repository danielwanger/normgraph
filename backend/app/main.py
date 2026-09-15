"""Normgraph API — semantische Suche + Verweis-Navigation über deutsches Bundesrecht."""

import os
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

# Für lokale Entwicklung fällt das auf "*" zurück. Im Deployment ALLOWED_ORIGINS
# als kommagetrennte Liste setzen, z.B. "https://normgraph.netlify.app".
allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(norms_router)


@app.get("/health")
def health():
    return {"status": "ok"}