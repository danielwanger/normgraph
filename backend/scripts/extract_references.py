"""
Normgraph — Referenz-Extraktion

Liest norms.json (aus parse_laws.py) und extrahiert alle §/Art-Verweise
im Volltext jeder Norm. Erzeugt references.json mit gerichteten Kanten:
    {from_norm: (law_slug, bezeichnung), to_norm: (law_slug, bezeichnung), kontext}

Behandelt zwei Fälle:
  - Interner Verweis:  "§ 823" (impliziert: selbes Gesetz)
  - Externer Verweis:  "§ 823 BGB" (explizites Gesetz genannt)
  - Listen:            "§§ 28, 31a und 34" / "§§ 664 bis 670"

Die Auflösung von "664 bis 670" in Einzelnormen erfolgt erst beim
Laden in die DB (dort sind alle existierenden §-Nummern bekannt),
hier wird nur die Rohform extrahiert.

Usage:
    python extract_references.py --norms ./data/norms.json --out-dir ./data
"""

import argparse
import json
import re
from pathlib import Path

# Bekannte Gesetzeskürzel, die typischerweise nach einer §-Angabe stehen
# (Heuristik: 2-6 Großbuchstaben direkt nach der Norm-Nummer, z.B. "BGB", "StGB", "HGB")
LAW_ABBR_RE = re.compile(r"^[A-ZÄÖÜ][A-ZÄÖÜa-zäöüß]{1,15}$")

# Ein einzelner §/Art-Treffer mit optionalem Gesetzeskürzel danach
REF_RE = re.compile(
    r"(§{1,2}|Art\.?)\s*"
    r"([0-9]+[a-z]?)"
    r"((?:\s*(?:,|und|bis)\s*[0-9]+[a-z]?)*)"
    r"(?:\s+([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß]{1,15}))?"
)

# Deutsche Sätze kapitalisieren jedes Nomen, daher ist eine Blacklist
# ungeeignet ("§ 284. Ersatz..." würde "Ersatz" als Kürzel matchen).
# Robuster: nur akzeptieren, was ein TATSÄCHLICH im Korpus vorkommendes
# jurabk-Kürzel ist (aus laws.json geladen). Wird von load_known_abbrs()
# zur Laufzeit befüllt.
KNOWN_LAW_ABBRS: set[str] = set()


def load_known_abbrs(laws_json_path: Path):
    laws = json.loads(laws_json_path.read_text(encoding="utf-8"))
    for l in laws:
        if l.get("slug"):
            KNOWN_LAW_ABBRS.add(l["slug"].upper())

NUM_RE = re.compile(r"[0-9]+[a-z]?")


def expand_numbers(first: str, rest: str, joiner_text: str):
    """Baut aus '27' + ', 31a und 34' -> ['27', '31a', '34']."""
    nums = [first]
    if "bis" in joiner_text:
        # Bereich: nur Start/Ende, Zwischenwerte werden beim DB-Import aufgelöst
        end = NUM_RE.findall(joiner_text)
        if end:
            nums.append("__RANGE_TO__" + end[-1])
    else:
        nums.extend(NUM_RE.findall(joiner_text))
    return nums


def extract_refs_from_text(text: str, own_law_slug: str):
    refs = []
    for m in REF_RE.finditer(text):
        kennzeichen, first_num, rest, law_abbr = m.groups()
        if law_abbr and law_abbr.upper() not in KNOWN_LAW_ABBRS:
            law_abbr = None
        target_law = law_abbr if law_abbr else own_law_slug
        for num in expand_numbers(first_num, rest or "", rest or ""):
            refs.append({
                "target_law_slug": target_law.upper() if target_law else own_law_slug,
                "target_bezeichnung_raw": f"{kennzeichen} {num}".replace("__RANGE_TO__", ""),
                "is_range_end": num.startswith("__RANGE_TO__"),
                "is_external": bool(law_abbr),
            })
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--norms", required=True)
    ap.add_argument("--laws", help="Pfad zu laws.json (für bekannte Gesetzeskürzel). Default: neben --norms.")
    ap.add_argument("--out-dir", default="./data")
    args = ap.parse_args()

    norms_path = Path(args.norms)
    laws_path = Path(args.laws) if args.laws else norms_path.parent / "laws.json"
    load_known_abbrs(laws_path)

    norms = json.loads(norms_path.read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_refs = []
    for n in norms:
        if not n["volltext"]:
            continue
        refs = extract_refs_from_text(n["volltext"], n["law_slug"])
        for r in refs:
            all_refs.append({
                "from_law_slug": n["law_slug"],
                "from_bezeichnung": n["bezeichnung"],
                **r,
            })

    (out_dir / "references_raw.json").write_text(
        json.dumps(all_refs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Rohe Referenzen extrahiert: {len(all_refs)}")
    print(f"-> {out_dir / 'references_raw.json'}")
    print(
        "\nHinweis: Diese Referenzen sind noch nicht gegen die norms-Tabelle "
        "aufgelöst (z.B. Range-Auflösung 'bis', Bezeichnung -> norm_id). "
        "Das passiert im DB-Import-Skript, weil dort alle IDs bekannt sind."
    )


if __name__ == "__main__":
    main()