"""Postgres-Connection-Pool für die Normgraph-API."""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg2 import pool

load_dotenv()  # liest .env im Arbeitsverzeichnis, falls vorhanden

_pool: pool.ThreadedConnectionPool | None = None


def init_pool():
    global _pool
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL Umgebungsvariable nicht gesetzt.")
    _pool = pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=db_url)


def close_pool():
    if _pool:
        _pool.closeall()


@contextmanager
def get_conn():
    if _pool is None:
        raise RuntimeError("DB-Pool nicht initialisiert — init_pool() beim App-Start aufrufen.")
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)