# Normgraph

Semantischer Navigator für deutsches Bundesrecht — Embeddings +
Verweis-Graph über alle Normen von gesetze-im-internet.de.

## Pipeline

1. Repo klonen: `git clone https://github.com/bundestag/gesetze.git`
2. `python scripts/parse_laws.py --repo-path ./gesetze --out-dir ./data`
   → laws.json, norms.json
3. `python scripts/extract_references.py --norms ./data/norms.json --out-dir ./data`
   → references_raw.json (§/Art-Verweise, roh, noch nicht auf norm_id aufgelöst)
4. DB anlegen: `psql < schema.sql` (Postgres + pgvector)
5. Import-Skript (noch zu bauen): norms.json + references_raw.json in DB laden,
   dabei references_raw gegen norm_id auflösen (inkl. "bis"-Ranges)
6. Embedding-Skript (noch zu bauen): e5-large über alle norms.volltext,
   `passage:` Prefix, Batch-Insert in norms.embedding

## Stand

- Parser getestet: 4.549 Gesetze, 93.425 Normen aus dem Gesamtkorpus extrahiert
- Referenz-Extraktion getestet: BGB allein hat 2.625 interne §-Verweise
- Wichtiger Befund: explizite Cross-Law-Verweise ("§ X BGB") sind im
  Rohtext selten — die meisten Verweise sind gesetzesintern