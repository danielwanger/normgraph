"""
Normgraph — Ingest-Parser

Liest die Markdown-Dateien aus dem bundestag/gesetze-Repo
(https://github.com/bundestag/gesetze) und wandelt jede einzelne
Norm (§ oder Art.) in einen strukturierten Datensatz um.

Output: laws.json (Gesetzesmetadaten) + norms.json (einzelne Normen
mit Gliederungspfad und Volltext), bereit für den Embedding-Schritt.

Usage:
    python parse_laws.py --repo-path /path/to/gesetze-repo --out-dir ./data
"""

import argparse
import json
import re
import sys
import unicodedata
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict


# Erkennt Norm-Überschriften wie:
#   "§ 1 Beginn der Rechtsfähigkeit"
#   "§§ 3 bis 6 (weggefallen)"
#   "Art 1"
#   "Art. 12a"
NORM_HEADING_RE = re.compile(
    r"^(?:\([^)]*\)\s*)?(§{1,2}|Art\.?)\s*([0-9]+[a-z]?)"
    r"(?:\s+(?:bis|und)\s+([0-9]+[a-z]?))?\s*(.*)$"
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Norm:
    law_slug: str
    law_title: str
    gliederung: list = field(default_factory=list)  # z.B. ["Buch 1 - Allgemeiner Teil", "Abschnitt 1 - Personen"]
    bezeichnung: str = ""       # "§ 1" oder "Art 1"
    ueberschrift: str = ""      # "Beginn der Rechtsfähigkeit"
    volltext: str = ""
    weggefallen: bool = False


def parse_frontmatter(text: str):
    """Extrahiert YAML-Frontmatter (--- ... ---) am Dateianfang."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    rest = text[m.end():]
    return meta, rest


def is_norm_heading(text: str):
    """Prüft ob eine Überschrift eine Norm (§/Art) ist, statt Gliederung (Buch/Abschnitt/Titel)."""
    return bool(NORM_HEADING_RE.match(text.strip()))


def parse_law_file(path: Path) -> list[Norm]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(raw)

    law_slug = meta.get("jurabk") or meta.get("slug") or path.parent.name
    law_title = meta.get("Title") or meta.get("title") or law_slug

    norms: list[Norm] = []
    gliederung_stack: list[tuple[int, str]] = []  # (level, text)

    current_norm: Norm | None = None
    buffer: list[str] = []

    def flush_norm():
        nonlocal current_norm, buffer
        if current_norm is not None:
            text = "\n".join(buffer).strip()
            text = re.sub(r"\n{3,}", "\n\n", text)
            current_norm.volltext = text
            current_norm.weggefallen = "(weggefallen)" in text or "(weggefallen)" in current_norm.ueberschrift
            norms.append(current_norm)
        current_norm = None
        buffer = []

    for line in body.splitlines():
        h = HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            heading_text = h.group(2).strip()

            if is_norm_heading(heading_text):
                # Neue Norm beginnt -> vorherige abschließen
                flush_norm()
                nm = NORM_HEADING_RE.match(heading_text)
                kennzeichen, nr, bis, rest = nm.groups()
                bezeichnung = f"{kennzeichen} {nr}" + (f" bis {bis}" if bis else "")
                current_norm = Norm(
                    law_slug=law_slug,
                    law_title=law_title,
                    gliederung=[t for _, t in gliederung_stack],
                    bezeichnung=bezeichnung.strip(),
                    ueberschrift=rest.strip(),
                )
            else:
                # Gliederungs-Ebene (Buch/Abschnitt/Titel/Kapitel/Präambel etc.)
                flush_norm()
                # Stack auf aktuelles Level zurückschneiden
                gliederung_stack = [(lv, t) for lv, t in gliederung_stack if lv < level]
                gliederung_stack.append((level, heading_text))
        else:
            if current_norm is not None:
                buffer.append(line)

    flush_norm()
    return norms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-path", required=True, help="Pfad zum geklonten bundestag/gesetze-Repo")
    ap.add_argument("--out-dir", default="./data")
    ap.add_argument("--limit", type=int, default=None, help="Nur die ersten N Gesetze verarbeiten (zum Testen)")
    args = ap.parse_args()

    repo = Path(args.repo_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    index_files = sorted(repo.glob("*/*/index.md"))
    if args.limit:
        index_files = index_files[: args.limit]

    print(f"Gefundene Gesetzesdateien: {len(index_files)}", file=sys.stderr)

    all_laws = []
    all_norms = []
    errors = []

    for i, path in enumerate(index_files, 1):
        try:
            norms = parse_law_file(path)
        except Exception as e:
            errors.append((str(path), str(e)))
            continue

        if not norms:
            continue

        law_slug = norms[0].law_slug
        law_title = norms[0].law_title
        all_laws.append({"slug": law_slug, "title": law_title, "quelle": str(path)})

        for n in norms:
            all_norms.append(asdict(n))

        if i % 500 == 0:
            print(f"  ... {i}/{len(index_files)} Gesetze verarbeitet", file=sys.stderr)

    (out_dir / "laws.json").write_text(
        json.dumps(all_laws, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "norms.json").write_text(
        json.dumps(all_norms, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nFertig.", file=sys.stderr)
    print(f"  Gesetze:  {len(all_laws)}", file=sys.stderr)
    print(f"  Normen:   {len(all_norms)}", file=sys.stderr)
    print(f"  Fehler:   {len(errors)}", file=sys.stderr)
    if errors:
        (out_dir / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  -> Details in {out_dir / 'errors.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()