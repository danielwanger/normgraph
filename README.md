# Normgraph

Semantischer Navigator für deutsches Bundesrecht — Embeddings +
Verweis-Graph über alle Normen von gesetze-im-internet.de.

## Architektur

```
normgraph/
├── backend/
│   ├── app/                  # FastAPI-App
│   │   ├── main.py
│   │   ├── db.py              # Connection-Pool
│   │   ├── embeddings.py      # Query-Embedding (e5-base)
│   │   └── routers/norms.py   # /search, /norms/{id}, /norms/{id}/references, /laws, /laws/{slug}/norms
│   ├── scripts/                # Einmalige Daten-Pipeline
│   │   ├── parse_laws.py
│   │   ├── extract_references.py
│   │   ├── import_to_db.py
│   │   └── embed_norms.py
│   ├── schema.sql
│   └── requirements.txt
└── frontend/                  # React + Vite
    └── src/
        ├── App.jsx             # Routing, Modus-Tabs (Suche/Gesetze)
        ├── api.js
        └── components/
            ├── SearchPanel.jsx     # Suche mit Gesetzes-Filter
            ├── ResultsList.jsx
            ├── NormReader.jsx      # Norm-Detail + Verweis-Graph
            ├── ReferenceGraph.jsx  # SVG-Verweis-Visualisierung
            ├── LawBrowser.jsx
            └── LawNormsReader.jsx
```

## Datenpipeline (einmalig, gegen die Supabase-DB)

1. Repo klonen: `git clone https://github.com/bundestag/gesetze.git repo`
2. `python backend/scripts/parse_laws.py --repo-path ./repo --out-dir ./data`
   → laws.json, norms.json
3. `python backend/scripts/extract_references.py --norms ./data/norms.json --out-dir ./data`
   → references_raw.json
4. Schema in Supabase laden (SQL Editor, Inhalt von `backend/schema.sql`)
5. `python backend/scripts/import_to_db.py --data-dir ./data --db-url "..."`
6. `python backend/scripts/embed_norms.py --db-url "..." --batch-size 64`
   → e5-base-Embeddings, läuft am schnellsten mit lokaler GPU

## Backend starten

```
cd backend
pip install -r requirements.txt
# .env mit DATABASE_URL anlegen (siehe .env.example)
uvicorn app.main:app --reload
```
→ `http://localhost:8000/docs` für die interaktive API-Doku.

## Frontend starten

```
cd frontend
npm install
npm run dev
```
→ `http://localhost:5173`, erwartet das Backend unter `localhost:8000`.

## Stand

- **Datenpipeline:** fertig und verifiziert — 4.549 Gesetze, 89.669 Normen,
  58.978 Verweis-Kanten. Parser-Bug (Tabellen-Referenzen wie "(zu § 4 ...)"
  fälschlich als eigene Norm erkannt) behoben.
- **Embeddings:** e5-base (768-dim, `halfvec`), inkl. `ivfflat`-Index —
  Umstieg von e5-large nötig, weil Daten + Index sonst nicht ins
  Supabase-Free-Tier-Limit (500MB) passten.
- **Backend:** FastAPI, alle Kern-Endpoints fertig und gegen echte Daten
  getestet. Semantische Suche liefert korrekte Treffer (z.B. § 355 BGB für
  "Widerrufsrecht bei Verbraucherverträgen").
- **Frontend:** React + Vite. Suche mit Gesetzes-Filter, URL-Routing,
  SVG-Verweis-Graph (radiales 1-Hop-Netz um die aktuelle Norm),
  Gesetzes-Browser.
- **Wichtiger Befund:** explizite Cross-Law-Verweise ("§ X BGB") sind im
  Rohtext selten — die meisten Verweise sind gesetzesintern.

## Offen / nächste Schritte

- Deployment (Backend + Frontend hosten, Domain verbinden)
- Verlinkung von Ynapse aus unter "German Law"