"""
Normgraph — DB-Import

Lädt laws.json, norms.json und references_raw.json in Postgres
(Schema siehe backend/schema.sql). Löst dabei:
  - Bezeichnung -> norm_id (pro Gesetz)
  - "bis"-Ranges in references_raw zu Einzelkanten auf
  - Externe Verweise nur, wenn das Zielgesetz + die Ziel-Norm tatsächlich existieren

Usage:
    python import_to_db.py --data-dir ./data --db-url postgresql://user:pass@host/db
"""

import argparse
import json
import re
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

NUM_ORDER_RE = re.compile(r"^([0-9]+)([a-z]?)$")


def sort_key(nr: str):
    m = NUM_ORDER_RE.match(nr)
    if not m:
        return (0, "")
    return (int(m.group(1)), m.group(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--db-url", required=True)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    laws = json.loads((data_dir / "laws.json").read_text(encoding="utf-8"))
    norms = json.loads((data_dir / "norms.json").read_text(encoding="utf-8"))
    refs_raw = json.loads((data_dir / "references_raw.json").read_text(encoding="utf-8"))

    conn = psycopg2.connect(args.db_url)
    cur = conn.cursor()

    # --- 1. Gesetze einfügen ---
    print(f"Importiere {len(laws)} Gesetze ...")
    law_id_by_slug = {}
    for l in laws:
        cur.execute(
            """INSERT INTO laws (slug, title, quelle_pfad) VALUES (%s, %s, %s)
               ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title
               RETURNING id""",
            (l["slug"], l["title"], l.get("quelle")),
        )
        law_id_by_slug[l["slug"]] = cur.fetchone()[0]
    conn.commit()

    # --- 2. Normen einfügen ---
    print(f"Importiere {len(norms)} Normen ...")
    # norm_id_by_key: (law_slug, bezeichnung) -> id ; zusätzlich (law_slug, nummer_only) für Referenzauflösung
    norm_id_by_full = {}
    norm_ids_by_law_and_number = {}  # (law_slug, "823") -> norm_id  (für Range-Auflösung)

    rows_by_key = {}
    duplicates = 0
    for n in norms:
        law_id = law_id_by_slug.get(n["law_slug"])
        if law_id is None:
            continue
        key = (law_id, n["bezeichnung"])
        if key in rows_by_key:
            duplicates += 1
        # Bei Duplikaten gewinnt der letzte Eintrag (meist die vollständigere Fassung)
        rows_by_key[key] = (
            law_id, n["gliederung"], n["bezeichnung"], n["ueberschrift"],
            n["volltext"], n["weggefallen"],
        )
    rows = list(rows_by_key.values())
    if duplicates:
        print(f"  Hinweis: {duplicates} doppelte (Gesetz, Bezeichnung)-Kombinationen gefunden, jeweils letzte Fassung behalten.")

    inserted = execute_values(
        cur,
        """INSERT INTO norms (law_id, gliederung, bezeichnung, ueberschrift, volltext, weggefallen)
           VALUES %s
           ON CONFLICT (law_id, bezeichnung) DO UPDATE SET volltext = EXCLUDED.volltext
           RETURNING id, law_id, bezeichnung""",
        rows,
        fetch=True,
    )
    conn.commit()

    law_slug_by_id = {v: k for k, v in law_id_by_slug.items()}
    for norm_id, law_id, bezeichnung in inserted:
        law_slug = law_slug_by_id[law_id]
        norm_id_by_full[(law_slug, bezeichnung)] = norm_id
        # Für Ranges: extrahiere Einzelnummern aus z.B. "§§ 664 bis 670"
        nums = re.findall(r"[0-9]+[a-z]?", bezeichnung)
        for num in nums:
            norm_ids_by_law_and_number.setdefault((law_slug, num), norm_id)

    print(f"  {len(norm_id_by_full)} Normen mit ID versehen.")

    # --- 3. Referenzen auflösen und einfügen ---
    print(f"Löse {len(refs_raw)} rohe Referenzen auf ...")

    # Referenzen sind zeilenweise mit is_range_end-Flags aufgeteilt (aus extract_references.py).
    # Wir gruppieren aufeinanderfolgende (from, target_law) mit is_range_end, um "bis"-Paare zu erkennen.
    edges = set()
    skipped_unresolved = 0

    i = 0
    while i < len(refs_raw):
        r = refs_raw[i]
        from_key = (r["from_law_slug"], r["from_bezeichnung"])
        from_id = norm_id_by_full.get(from_key)

        target_law = r["target_law_slug"]
        target_num = re.search(r"[0-9]+[a-z]?", r["target_bezeichnung_raw"])
        target_num = target_num.group(0) if target_num else None

        if from_id is None or target_num is None:
            skipped_unresolved += 1
            i += 1
            continue

        if r["is_range_end"] and i > 0:
            # Range: vorherige Zeile war Start, diese ist Ende -> alle dazwischen verbinden
            prev = refs_raw[i - 1]
            start_num = re.search(r"[0-9]+[a-z]?", prev["target_bezeichnung_raw"])
            if start_num and prev["from_law_slug"] == r["from_law_slug"] and prev["from_bezeichnung"] == r["from_bezeichnung"]:
                start_n, end_n = start_num.group(0), target_num
                # Nur numerische Ranges ohne Buchstaben-Suffix auflösen (Standardfall)
                try:
                    lo, hi = int(re.match(r"[0-9]+", start_n).group()), int(re.match(r"[0-9]+", end_n).group())
                    for n in range(lo, hi + 1):
                        tid = norm_ids_by_law_and_number.get((target_law, str(n)))
                        if tid:
                            edges.add((from_id, tid, target_law != r["from_law_slug"]))
                except ValueError:
                    pass
            i += 1
            continue

        to_id = norm_ids_by_law_and_number.get((target_law, target_num))
        if to_id:
            edges.add((from_id, to_id, r["is_external"]))
        else:
            skipped_unresolved += 1
        i += 1

    print(f"  Aufgelöste Kanten: {len(edges)} (nicht auflösbar: {skipped_unresolved})")

    execute_values(
        cur,
        """INSERT INTO norm_references (from_norm_id, to_norm_id, is_external)
           VALUES %s ON CONFLICT (from_norm_id, to_norm_id) DO NOTHING""",
        list(edges),
    )
    conn.commit()

    cur.close()
    conn.close()
    print("\nImport abgeschlossen.")


if __name__ == "__main__":
    main()