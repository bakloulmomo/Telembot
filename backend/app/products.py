"""Registro dei prodotti: id stabile ↔ cartella del manuale.

L'elenco vive in shared/products.json, così il motore RAG usa gli stessi id
senza dipendere dal backend.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.manuals import LANGS

Category = Literal["robot", "accessory"]


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    category: Category
    folder: str      # relativo a data/
    path: Path       # assoluto

    @property
    def langs(self) -> list[str]:
        # ricavate dai file: FlashBot, GW1 e Pager non hanno it.md
        return [lang for lang in LANGS if (self.path / f"{lang}.md").exists()]

    def md_file(self, lang: str) -> Path:
        return self.path / f"{lang}.md"


def load_products(products_file: Path, data_dir: Path) -> list[Product]:
    raw = json.loads(products_file.read_text(encoding="utf-8"))
    products = [Product(path=data_dir / p["folder"], **p) for p in raw]

    ids = [p.id for p in products]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"Id duplicati in {products_file}")
    missing = [p.folder for p in products if not p.path.is_dir()]
    if missing:
        raise RuntimeError(f"Cartelle mancanti in {data_dir}: {missing}. Controlla DATA_DIR nel file .env.")
    return products
