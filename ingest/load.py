"""Create the tables and load products and manual sections into Postgres.

No embeddings are created here: run embed.py afterwards.

    python ingest/load.py --only bellabot-pro charging-station-light   # pilot
    python ingest/load.py                                              # all 22 products

Re-running is safe: rows are updated in place. If a section's text changed, its
embedding is cleared so that embed.py creates it again.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from psycopg.types.json import Jsonb

import db
from app.manuals import LANGS, Manual, Section, parse_manual  # backend/app/manuals.py

# --- figures -----------------------------------------------------------------

IMAGE_LINE_RE = re.compile(r"^!\[([^\]]*)\]\((images/[^)\s]+)\)")
AI_DESC_RE = re.compile(r"^>\s*\*(?:Figure description \(AI\)|Bildbeschreibung \(KI\)|Descrizione della figura \(IA\)):?\*:?\s*(.*)$")
LABELS_RE = re.compile(r"^\*(?:Labels|Beschriftungen|Etichette):?\*:?\s*$")
LABEL_ITEM_RE = re.compile(r"^\s*[-*]\s+(?:\*\*(.+?)\*\*\s*)?(.*)$")
HEADING_RE = re.compile(r"^#{1,6}\s")


def extract_figures(product_id: str, lang: str, section: Section) -> list[dict]:
    """Figures of a section, with the labels printed in the PDF.

    The AI description is not always on the line after the image, so we look ahead
    until the next image or heading. A label list belongs to the figure before it;
    if the section has no figure yet (some Italian manuals print the list first),
    it belongs to the next figure.
    """
    figures: list[dict] = []
    current: dict | None = None
    pending: list[dict] = []     # labels printed before their figure
    in_labels = False
    caption = f"{section.number} {section.title}".strip() if section.number else section.title
    for line in section.lines:
        if m := IMAGE_LINE_RE.match(line):
            path = m.group(2)
            current = {
                "id": f"{product_id}:{lang}:{Path(path).stem.split('-', 1)[-1]}",
                "path": path,
                "caption": caption,
                "alt": m.group(1) if m.group(1) not in ("", "Image", "Image (added from the PDF)") else None,
                "labels": pending,
                "has_ai_description": False,
            }
            pending = []
            figures.append(current)
            in_labels = False
            continue
        if HEADING_RE.match(line):
            in_labels = False
            continue
        if AI_DESC_RE.match(line):
            if current is not None:
                current["has_ai_description"] = True
            in_labels = False
        elif LABELS_RE.match(line):
            in_labels = True
        elif in_labels and (m := LABEL_ITEM_RE.match(line)) and line.strip():
            target = current["labels"] if current is not None else pending
            target.append({"n": m.group(1), "text": m.group(2).strip()})
        elif in_labels and line.strip():
            in_labels = False
    return figures


# --- section kind ------------------------------------------------------------
# Checked in this order against the section title, then against its chapter title.

KIND_RULES: list[tuple[str, str]] = [
    ("troubleshooting", r"trouble ?shoot|fault|fehler|störung|risoluzione|guast|problem"),
    ("specs", r"specification|parameter|technische daten|spezifikation|specifiche|parametri"),
    ("compliance", r"complian|regulat|fcc|\bic\b|\bce\b|declaration|konformit|vorschrift|conformit|normativ|disposal|entsorgung|smaltimento|recycl"),
    ("warranty", r"after-?sales|warranty|garantie|gewährleistung|kundendienst|garanzia|post-?vendita|assistenza"),
    ("safety", r"safety|sicherheit|sicurezza|warning|warnhinweis|avvertenz|precaution"),
    ("maintenance", r"maintenan|care\b|servicing|cleaning|wartung|pflege|reinigung|manutenzione|cura\b|pulizia"),
    ("compatibility", r"compatib|kompatib"),
    ("components", r"appearance|component|aussehen|erscheinungsbild|bestandteil|kennenlernen|komponent|bauteil|aspetto|componenti"),
    ("overview", r"overview|introduction|überblick|übersicht|einführung|panoramica|introduzione|packing list|lieferumfang|packliste|contenuto della confezione|elenco"),
    ("usage", r"how to use|instruction|operation|usage|bedienung|verwendung|anleitung|utilizzo|uso\b|istruzioni|charging|laden|ricarica|mapping|lagepl|mappa|button|tasten|pulsant|mode|modus|modalit|indicator|anzeige|indicator|install"),
]
_KIND_RES = [(kind, re.compile(rx, re.I)) for kind, rx in KIND_RULES]


# A chapter of one of these kinds decides the kind of all its sections
# ("1.1 Power usage" inside "1. Safety instructions" is safety, not usage).
CHAPTER_FIRST = {"safety", "compliance", "warranty"}


def classify(key: str, title: str, chapter_title: str) -> str:
    if key == "0":
        return "front_matter"          # copyright and notes before the first numbered heading
    for kind, rx in _KIND_RES:
        if kind in CHAPTER_FIRST and chapter_title and rx.search(chapter_title):
            return kind
    for text in (title, chapter_title):
        for kind, rx in _KIND_RES:
            if text and rx.search(text):
                return kind
    return "other"


# --- products ----------------------------------------------------------------

OVERVIEW_TITLE_RE = re.compile(
    r"(product )?overview|introduction|überblick|übersicht|produktübersicht|einführung|panoramica|introduzione", re.I)


def overview_paragraph(manual: Manual) -> str | None:
    for s in manual.sections:
        if s.number and OVERVIEW_TITLE_RE.fullmatch(s.title.strip()):
            for para in s.markdown.split("\n\n"):
                para = para.strip()
                if para and not para.startswith(("#", "!", ">", "|", "*", "-")):
                    return para
    return None


def load_registry() -> list[dict]:
    products = json.loads(db.PRODUCTS_FILE.read_text(encoding="utf-8"))
    extras = json.loads((db.PRODUCTS_FILE.parent / "product_extras.json").read_text(encoding="utf-8"))
    for p in products:
        extra = extras.get(p["id"])
        if extra is None:
            raise SystemExit(f"shared/product_extras.json has no entry for '{p['id']}'")
        p.update(extra)
    return products


def block_type(markdown: str) -> str:
    lines = [l for l in markdown.splitlines() if l.strip()]
    table_lines = sum(1 for l in lines if l.lstrip().startswith("|"))
    return "table" if lines and table_lines * 2 > len(lines) else "text"


# --- main --------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", metavar="PRODUCT_ID", help="load only these products (pilot run)")
    args = ap.parse_args()

    registry = load_registry()
    known = {p["id"] for p in registry}
    if args.only and (unknown := set(args.only) - known):
        raise SystemExit(f"Unknown product ids: {sorted(unknown)}")
    selected = [p for p in registry if not args.only or p["id"] in args.only]

    with db.connect(vectors=False) as conn:
        conn.execute((Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))

        total_chunks = total_figures = 0
        for p in selected:
            folder = db.DATA_DIR / p["folder"]
            manuals = {lang: parse_manual(folder / f"{lang}.md", lang)
                       for lang in LANGS if (folder / f"{lang}.md").is_file()}
            if "en" not in manuals:
                raise SystemExit(f"No en.md found for {p['id']} in {folder}")
            overview = {lang: text for lang, m in manuals.items() if (text := overview_paragraph(m))}

            conn.execute(
                """
                INSERT INTO products (id, name, kind, family, aliases, langs, folder, related_products, overview)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name, kind = EXCLUDED.kind, family = EXCLUDED.family,
                    aliases = EXCLUDED.aliases, langs = EXCLUDED.langs, folder = EXCLUDED.folder,
                    related_products = EXCLUDED.related_products, overview = EXCLUDED.overview
                """,
                (p["id"], p["name"], p["category"], p["family"], p["aliases"], list(manuals),
                 p["folder"], p["related_products"], Jsonb(overview)),
            )

            n_chunks = n_figs = 0
            for lang, manual in manuals.items():
                chapter_title = ""
                keys = []
                for seq, s in enumerate(manual.sections):
                    if s.level <= 1:
                        chapter_title = s.title
                    content = s.markdown
                    if not content:
                        continue  # a chapter heading with no text of its own
                    figures = extract_figures(p["id"], lang, s)
                    keys.append(s.key)
                    conn.execute(
                        """
                        INSERT INTO chunks (product_id, lang, section_key, section_title, section_kind,
                                            block_type, seq, page, pdf_page, content, figures)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (product_id, lang, section_key) DO UPDATE SET
                            section_title = EXCLUDED.section_title, section_kind = EXCLUDED.section_kind,
                            block_type = EXCLUDED.block_type, seq = EXCLUDED.seq, page = EXCLUDED.page,
                            pdf_page = EXCLUDED.pdf_page, figures = EXCLUDED.figures,
                            embedding = CASE WHEN chunks.content = EXCLUDED.content
                                             AND chunks.section_title IS NOT DISTINCT FROM EXCLUDED.section_title
                                             THEN chunks.embedding END,
                            content = EXCLUDED.content
                        """,
                        (p["id"], lang, s.key, s.title, classify(s.key, s.title, chapter_title), block_type(content),
                         seq, s.page, s.pdf_page, content, Jsonb(figures)),
                    )
                    n_chunks += 1
                    n_figs += len(figures)
                # sections that no longer exist in the manual
                conn.execute("DELETE FROM chunks WHERE product_id = %s AND lang = %s AND NOT (section_key = ANY(%s))",
                             (p["id"], lang, keys))
            print(f"{p['id']:<24} langs={','.join(manuals):<9} sections={n_chunks:<4} figures={n_figs}")
            total_chunks += n_chunks
            total_figures += n_figs

        conn.commit()
    print(f"\nLoaded {len(selected)} products, {total_chunks} sections, {total_figures} figures.")


if __name__ == "__main__":
    main()
