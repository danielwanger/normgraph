"""Normgraph API-Endpoints."""

from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.db import get_conn
from app.embeddings import embed_query

router = APIRouter()


@router.get("/laws")
def list_laws(q: str | None = Query(None, description="Optionale Textsuche im Gesetzestitel")):
    """Liste aller Gesetze, optional gefiltert nach Titel/Kürzel."""
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        if q:
            cur.execute(
                "SELECT id, slug, title FROM laws WHERE title ILIKE %s OR slug ILIKE %s ORDER BY slug",
                (f"%{q}%", f"%{q}%"),
            )
        else:
            cur.execute("SELECT id, slug, title FROM laws ORDER BY slug")
        return cur.fetchall()


@router.get("/laws/{slug}/norms")
def list_norms_for_law(slug: str):
    """Alle Normen eines Gesetzes, in Dokumentreihenfolge (nach id)."""
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT n.id, n.bezeichnung, n.ueberschrift, n.gliederung, n.weggefallen
               FROM norms n JOIN laws l ON n.law_id = l.id
               WHERE l.slug = %s ORDER BY n.id""",
            (slug,),
        )
        rows = cur.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail=f"Gesetz '{slug}' nicht gefunden oder ohne Normen.")
        return rows


@router.get("/norms/{norm_id}")
def get_norm(norm_id: int):
    """Details einer einzelnen Norm inkl. Gesetzeskontext."""
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT n.id, n.bezeichnung, n.ueberschrift, n.gliederung, n.volltext,
                      n.weggefallen, l.slug AS law_slug, l.title AS law_title
               FROM norms n JOIN laws l ON n.law_id = l.id
               WHERE n.id = %s""",
            (norm_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Norm nicht gefunden.")
        return row


@router.get("/norms/{norm_id}/references")
def get_norm_references(norm_id: int):
    """Verweis-Graph um eine Norm: worauf sie verweist, und was auf sie verweist."""
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id FROM norms WHERE id = %s", (norm_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Norm nicht gefunden.")

        cur.execute(
            """SELECT n.id, n.bezeichnung, n.ueberschrift, l.slug AS law_slug, r.is_external
               FROM norm_references r JOIN norms n ON r.to_norm_id = n.id
               JOIN laws l ON n.law_id = l.id
               WHERE r.from_norm_id = %s ORDER BY n.id""",
            (norm_id,),
        )
        outgoing = cur.fetchall()

        cur.execute(
            """SELECT n.id, n.bezeichnung, n.ueberschrift, l.slug AS law_slug, r.is_external
               FROM norm_references r JOIN norms n ON r.from_norm_id = n.id
               JOIN laws l ON n.law_id = l.id
               WHERE r.to_norm_id = %s ORDER BY n.id""",
            (norm_id,),
        )
        incoming = cur.fetchall()

        return {"verweist_auf": outgoing, "wird_zitiert_von": incoming}


@router.get("/search")
def search_norms(
    q: str = Query(..., min_length=2, description="Suchanfrage (natürlichsprachlich)"),
    limit: int = Query(10, ge=1, le=50),
    law_slug: str | None = Query(None, description="Optional: Suche auf ein Gesetz beschränken"),
):
    """
    Semantische Suche über alle Normen per Cosine-Similarity.

    Hinweis: läuft aktuell ohne ivfflat-Index (Speicherplatzgründe, siehe
    schema.sql) — bei ~90k Normen ist eine sequenzielle Suche noch im
    Sekundenbereich, wird aber mit wachsendem Korpus irgendwann spürbar
    langsamer. Dann: Index wieder aktivieren oder auf mehr Speicher upgraden.
    """
    query_embedding = embed_query(q)

    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        if law_slug:
            cur.execute(
                """SELECT n.id, n.bezeichnung, n.ueberschrift, l.slug AS law_slug, l.title AS law_title,
                          1 - (n.embedding <=> %s::halfvec) AS similarity
                   FROM norms n JOIN laws l ON n.law_id = l.id
                   WHERE n.embedding IS NOT NULL AND l.slug = %s
                   ORDER BY n.embedding <=> %s::halfvec
                   LIMIT %s""",
                (query_embedding, law_slug, query_embedding, limit),
            )
        else:
            cur.execute(
                """SELECT n.id, n.bezeichnung, n.ueberschrift, l.slug AS law_slug, l.title AS law_title,
                          1 - (n.embedding <=> %s::halfvec) AS similarity
                   FROM norms n JOIN laws l ON n.law_id = l.id
                   WHERE n.embedding IS NOT NULL
                   ORDER BY n.embedding <=> %s::halfvec
                   LIMIT %s""",
                (query_embedding, query_embedding, limit),
            )
        return cur.fetchall()