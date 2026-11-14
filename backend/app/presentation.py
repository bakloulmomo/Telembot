"""Campi in più per l'interfaccia, calcolati dal backend senza AI (DATA.md del design).

- clarification: la domanda di chiarimento divisa in domanda e motivo, le scelte con una descrizione;
- comparison: la tabella di confronto quando la risposta parla di due o più prodotti.

Gli altri campi del design (style, short_answer, gaps[].topic, cited_lines) richiedono il modello:
li deve mandare il motore RAG; senza, l'interfaccia usa i suoi ripieghi.
"""

from __future__ import annotations

import re

from app.catalog import SPEC_LABELS, Catalog
from app.schemas import Citation

_CITE_RE = re.compile(r"\s*\[\d+\]")
_COMPARE_RE = re.compile(r"compar|confront|vergleich", re.I)

# righe della tabella, nell'ordine del design (DESIGN-SPEC 1.10), al massimo MAX_ROWS
ROW_ORDER = ["min_width", "battery_life", "charging_time", "trays", "tray_load", "cleaning_width",
             "water_tank", "productivity", "speed", "battery_capacity", "weight"]
PLAIN_LABELS_EN = {"min_width": "Narrowest aisle", "battery_life": "Runs on one charge",
                   "charging_time": "Time to charge", "trays": "Trays", "tray_load": "Load per tray"}
MAX_ROWS = 6
MAX_PRODUCTS = 4


def clarification(answer: str, options: list[str], catalog: Catalog) -> dict | None:
    """{"question", "reason", "options": [{"label", "detail"}]} dal testo del chiarimento."""
    if not options:
        return None
    text = _CITE_RE.sub("", answer).strip()
    first, _, rest = text.partition("\n")
    if not rest and "?" in first:                     # tutto su una riga: la domanda finisce al "?"
        first, rest = first[:first.index("?") + 1], first[first.index("?") + 1:]
    names = {p.name.lower() for p in catalog.products}

    def detail(label: str) -> str:
        if label.lower() in names:
            return f"{label} User Manual"
        return "Side by side, each value with its source" if _COMPARE_RE.search(label) else ""

    return {"question": first.strip(), "reason": " ".join(rest.split()),
            "options": [{"label": o, "detail": detail(o)} for o in options]}


def comparison(catalog: Catalog, citations: list[Citation], lang: str | None) -> dict | None:
    """{"products": [{"id", "name", "n"}], "recommended": [], "rows": [{"label", "values"}]} con i valori
    delle schede tecniche, copiati come stampati nei manuali."""
    ids = list(dict.fromkeys(c.product_id for c in citations if c.product_id))[:MAX_PRODUCTS]
    if len(ids) < 2:
        return None
    lang = lang if lang in ("en", "de", "it") else "en"
    items = [catalog.get(pid) for pid in ids]
    rows = []
    for key in ROW_ORDER:
        values = {d.product.id: d.specs.get(key) for d in items}
        if any(values.values()):
            label = PLAIN_LABELS_EN.get(key) if lang == "en" else None
            rows.append({"label": label or SPEC_LABELS[key].get(lang, SPEC_LABELS[key]["en"]), "values": values})
        if len(rows) == MAX_ROWS:
            break
    if not rows:
        return None
    first_n = {}
    for c in citations:
        first_n.setdefault(c.product_id, c.n)
    return {"products": [{"id": d.product.id, "name": d.product.name, "n": first_n.get(d.product.id)} for d in items],
            "recommended": [], "rows": rows}
