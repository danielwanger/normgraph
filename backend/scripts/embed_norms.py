"""
Normgraph — Embedding-Skript

Berechnet Embeddings für alle Normen ohne Embedding und schreibt sie
in die Postgres-DB (Spalte norms.embedding, pgvector).

Nutzt multilingual-e5-large (1024-dim), gleiches Modell wie bei Ynapse,
mit "passage: " Prefix für die zu embeddenden Normtexte (e5-Konvention:
Dokumente = "passage:", Suchanfragen = "query:" — siehe search.py).

Für die Embedding-Eingabe wird Überschrift + Volltext kombiniert, damit
kurze materiell-arme Paragraphen (z.B. reine Verweisnormen) trotzdem
einen inhaltlich informativen Vektor bekommen.

Läuft in Batches mit Checkpointing (commit nach jedem Batch), damit ein
Abbruch bei 93k Normen nicht bei Null neu anfängt.

Usage:
    python embed_norms.py --db-url postgresql://user:pass@host/db --batch-size 64
"""

import argparse
import sys
import time

import psycopg2
import torch
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-base"

# e5-large hat ein Kontextlimit von 512 Tokens; sehr lange Normen (Anlagen/Tabellen,
# die dem Parser fälschlich zugeordnet wurden) würden ohne Kappung die Tokenisierung
# und Attention-Berechnung unnötig aufblähen (~30s statt ~1-2s pro Batch beobachtet).
# ~1500 Zeichen ≈ 250-350 Tokens, sicher unter dem Limit, deckt den Kern des
# Paragraphen ab (Median-Norm hat nur 668 Zeichen).
MAX_PASSAGE_CHARS = 1500


def build_passage_text(ueberschrift: str, volltext: str) -> str:
    parts = []
    if ueberschrift:
        parts.append(ueberschrift.strip())
    if volltext:
        parts.append(volltext.strip()[:MAX_PASSAGE_CHARS])
    text = " — ".join(parts) if parts else ""
    # e5-Konvention: Dokumente bekommen den "passage:" Prefix
    return "passage: " + text if text else "passage: (kein Inhalt)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-url", required=True)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--limit", type=int, default=None, help="Nur die ersten N Normen (zum Testen)")
    ap.add_argument("--skip-weggefallen", action="store_true",
                     help="Weggefallene Normen (kein Volltext) nicht embedden")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Lade Modell {MODEL_NAME} auf Device '{device}' ...", file=sys.stderr)
    if device == "cuda":
        print(f"  GPU: {torch.cuda.get_device_name(0)}", file=sys.stderr)
    model = SentenceTransformer(MODEL_NAME, device=device)
    model.max_seq_length = 512  # explizit setzen, statt auf Tokenizer-Default zu vertrauen
    if device == "cuda":
        model.half()  # FP16 statt FP32 — auf GPU deutlich schneller, Qualitätsverlust vernachlässigbar

    conn = psycopg2.connect(args.db_url)
    cur = conn.cursor()

    where = "embedding IS NULL"
    if args.skip_weggefallen:
        where += " AND weggefallen = FALSE"

    cur.execute(f"SELECT COUNT(*) FROM norms WHERE {where}")
    total = cur.fetchone()[0]
    if args.limit:
        total = min(total, args.limit)
    print(f"Normen ohne Embedding: {total}", file=sys.stderr)

    processed = 0
    while processed < total or (args.limit is None and total > 0):
        limit_clause = f"LIMIT {args.batch_size}"
        cur.execute(f"""
            SELECT id, ueberschrift, volltext FROM norms
            WHERE {where}
            ORDER BY id
            {limit_clause}
        """)
        rows = cur.fetchall()
        if not rows:
            break

        ids = [r[0] for r in rows]
        texts = [build_passage_text(r[1], r[2]) for r in rows]

        t0 = time.time()
        embeddings = model.encode(
            texts, batch_size=args.batch_size, show_progress_bar=False, normalize_embeddings=True
        )
        t1 = time.time()

        if device == "cuda":
            torch.cuda.empty_cache()

        update_data = [(emb.tolist(), norm_id) for emb, norm_id in zip(embeddings, ids)]
        execute_values(
            cur,
            "UPDATE norms SET embedding = data.embedding FROM (VALUES %s) AS data(embedding, id) WHERE norms.id = data.id",
            update_data,
            template="(%s::halfvec, %s)",
        )
        conn.commit()
        t2 = time.time()

        processed += len(rows)
        print(f"  {processed}/{total} embedded  (encode: {t1-t0:.1f}s, db-write: {t2-t1:.1f}s)", file=sys.stderr)

        if args.limit and processed >= args.limit:
            break

    cur.close()
    conn.close()
    print("\nEmbedding abgeschlossen.", file=sys.stderr)


if __name__ == "__main__":
    main()