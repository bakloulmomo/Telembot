"""Catalogo in memoria: manuali analizzati, specifiche, URL di fonti e file.

Si costruisce una volta all'avvio leggendo data/ (circa un secondo) e non
scrive niente su disco. Non usa LLM: tutto ciò che restituisce si ritrova
alla lettera nei manuali.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from app.manuals import IMAGE_RE, Manual, Section, parse_manual, parse_tables
from app.products import Product, load_products

# --- specifiche normalizzate --------------------------------------------------
# (chiave, regex sull'etichetta inglese, etichette per lingua). Vince la prima
# riga della tabella che corrisponde. I valori restano quelli del manuale.
SPEC_FIELDS: list[tuple[str, str, dict[str, str]]] = [
    ("battery_capacity", r"battery capacity|battery$",
     {"en": "Battery capacity", "it": "Capacità batteria", "de": "Akkukapazität"}),
    ("battery_life", r"battery life|runtime|operation time of batteries",
     {"en": "Battery life", "it": "Autonomia", "de": "Akkulaufzeit"}),
    ("charging_time", r"charging time",
     {"en": "Charging time", "it": "Tempo di ricarica", "de": "Ladezeit"}),
    ("speed", r"cruise speed|max\.? moving speed",
     {"en": "Speed", "it": "Velocità", "de": "Geschwindigkeit"}),
    ("dimensions", r"(robot |overall |product )?dimensions(?! \(without)|body size",
     {"en": "Dimensions", "it": "Dimensioni", "de": "Abmessungen"}),
    ("weight", r"(robot |body |overall |product )?weight(?! \(without)",
     {"en": "Weight", "it": "Peso", "de": "Gewicht"}),
    ("min_width", r"min(imum|\.)? (travel|passing) width|min\.? path clearance",
     {"en": "Min. passage width", "it": "Larghezza min. di passaggio", "de": "Min. Durchfahrtsbreite"}),
    ("max_obstacle", r"max(imum|\.)? surmountable height",
     {"en": "Max. obstacle height", "it": "Altezza max. superabile", "de": "Max. überwindbare Höhe"}),
    ("max_gap", r"max(imum|\.)? surmountable gap",
     {"en": "Max. gap", "it": "Fessura max. superabile", "de": "Max. überwindbarer Spalt"}),
    ("climbing", r"max(imum|\.)? climbing angle",
     {"en": "Max. climbing angle", "it": "Pendenza max.", "de": "Max. Steigungswinkel"}),
    ("trays", r"(no\.|number) of trays",
     {"en": "Trays", "it": "Vassoi", "de": "Tabletts"}),
    ("tray_load", r"tray load|tray supporting capacity|max\. load|load capacity",
     {"en": "Load", "it": "Carico", "de": "Traglast"}),
    ("cleaning_width", r"cleaning width|working width|squeegee width",
     {"en": "Cleaning width", "it": "Larghezza di pulizia", "de": "Reinigungsbreite"}),
    ("productivity", r"productivity|cleaning efficiency",
     {"en": "Productivity", "it": "Produttività", "de": "Flächenleistung"}),
    ("water_tank", r"solution tank capacity|water tank capacity",
     {"en": "Water tank", "it": "Serbatoio acqua", "de": "Wassertank"}),
    ("navigation", r"navigation|positioning mode",
     {"en": "Navigation", "it": "Navigazione", "de": "Navigation"}),
    ("screen", r"screen size|screen specifications",
     {"en": "Screen", "it": "Schermo", "de": "Bildschirm"}),
    ("ip_rating", r"ip rating",
     {"en": "IP rating", "it": "Grado IP", "de": "Schutzart"}),
    ("operating_voltage", r"operating voltage|output voltage",
     {"en": "Voltage", "it": "Tensione", "de": "Spannung"}),
]
_SPEC_RES = [(key, re.compile(rf"^\s*(?:{rx})", re.I), labels) for key, rx, labels in SPEC_FIELDS]
SPEC_LABELS = {key: labels for key, _, labels in SPEC_FIELDS}
KEY_SPECS = ["battery_life", "speed", "tray_load", "cleaning_width", "min_width", "weight", "dimensions"]

SPEC_TITLE_RE = re.compile(
    r"specification|parameter|technische daten|spezifikation|specifiche|parametri|caratteristiche del prodotto", re.I)
OVERVIEW_TITLE_RE = re.compile(
    r"(product )?overview|introduction|überblick|übersicht|produktübersicht|einführung|panoramica|introduzione", re.I)
_GENERIC_HEADER_RE = re.compile(
    r"(description|beschreibung|descrizione|values?|wert|valore|parameters?|parametri|"
    r"specifications?|spezifikationen?|specifiche|details?|dettagli)?", re.I)


@dataclass
class ProductData:
    product: Product
    manuals: dict[str, Manual]                         # lingua → manuale
    specs: dict[str, str] = field(default_factory=dict)  # chiave normalizzata → valore (EN)

    def manual(self, lang: str | None) -> Manual:
        """Il manuale nella lingua richiesta, altrimenti quello inglese."""
        return self.manuals.get(lang or "en") or self.manuals["en"]


class Catalog:
    def __init__(self, products: list[Product]):
        self.products = products
        self.by_id: dict[str, ProductData] = {}
        for p in products:
            manuals = {lang: parse_manual(p.md_file(lang), lang) for lang in p.langs}
            if "en" not in manuals:
                raise RuntimeError(f"Manca en.md per {p.id}")
            data = ProductData(product=p, manuals=manuals)
            data.specs = self._normalized_specs(manuals["en"])
            self.by_id[p.id] = data

    @classmethod
    def load(cls, products_file: Path, data_dir: Path) -> "Catalog":
        return cls(load_products(products_file, data_dir))

    @property
    def section_count(self) -> int:
        return sum(len(m.sections) for d in self.by_id.values() for m in d.manuals.values())

    def get(self, product_id: str) -> ProductData | None:
        return self.by_id.get(product_id)

    # --- URL ------------------------------------------------------------------

    @staticmethod
    def file_url(product_id: str, rel_path: str) -> str:
        return f"/files/{product_id}/{quote(rel_path)}"

    @staticmethod
    def source_url(product_id: str, lang: str, key: str) -> str:
        return f"/api/sources/{product_id}/{lang}/{quote(key, safe='')}"

    def pdf_url(self, product_id: str, manual: Manual, pdf_page: int | None = None) -> str | None:
        if not manual.source_pdf or not (manual.path.parent / manual.source_pdf).is_file():
            return None
        url = self.file_url(product_id, manual.source_pdf)
        return f"{url}#page={pdf_page}" if pdf_page else url

    def rewrite_images(self, product_id: str, markdown: str) -> str:
        return IMAGE_RE.sub(lambda m: m.group(0).replace(m.group(1), self.file_url(product_id, m.group(1))), markdown)

    # --- contenuti ------------------------------------------------------------

    @staticmethod
    def spec_section(manual: Manual) -> Section | None:
        candidates = [s for s in manual.sections if s.number and SPEC_TITLE_RE.search(s.title) and "|" in s.markdown]
        chapter2 = [s for s in candidates if s.number.startswith("2")]
        return (chapter2 or candidates or [None])[0]

    @staticmethod
    def spec_tables(section: Section | None) -> list[tuple[list[str] | None, list[list[str]]]]:
        """Tabelle della sezione specifiche; l'intestazione è None se in realtà è una riga di dati."""
        if section is None:
            return []
        out = []
        for header, rows in parse_tables(section.markdown):
            if len(header) >= 2 and not _GENERIC_HEADER_RE.fullmatch(header[-1].strip()):
                out.append((None, [header, *rows]))
            else:
                out.append((header, rows))
        return out

    @classmethod
    def key_values(cls, section: Section | None) -> list[tuple[str, str]]:
        pairs = []
        for _, rows in cls.spec_tables(section):
            for cells in rows:
                if len(cells) < 2 or not cells[0]:
                    continue
                values = [c for c in dict.fromkeys(cells[1:]) if c and c != cells[0]]
                if values:
                    pairs.append((cells[0], " · ".join(values)))
        return pairs

    @classmethod
    def _normalized_specs(cls, manual_en: Manual) -> dict[str, str]:
        specs: dict[str, str] = {}
        for label, value in cls.key_values(cls.spec_section(manual_en)):
            for key, rx, _ in _SPEC_RES:
                if key not in specs and rx.match(label):
                    specs[key] = value
                    break
        return specs

    @staticmethod
    def overview(manual: Manual) -> str | None:
        for s in manual.sections:
            if s.number and s.number.startswith("2") and OVERVIEW_TITLE_RE.fullmatch(s.title.strip()):
                for para in s.markdown.split("\n\n"):
                    para = para.strip()
                    if para and not para.startswith(("#", "!", ">", "|", "*", "-")):
                        return para
        return None

    @staticmethod
    def thumbnail(manual: Manual) -> str | None:
        for s in manual.sections:
            if s.number and s.number.startswith("2") and s.images:
                return s.images[0]
        return None

    def localized_specs(self, data: ProductData, lang: str, keys: list[str] | None = None) -> list[tuple[str, str, str]]:
        order = keys or [k for k, _, _ in SPEC_FIELDS]
        return [(k, SPEC_LABELS[k].get(lang, SPEC_LABELS[k]["en"]), data.specs[k]) for k in order if k in data.specs]
