"""Database access and settings for the RAG engine."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from pgvector.psycopg import register_vector

REPO_DIR = Path(__file__).resolve().parent.parent
load_dotenv(REPO_DIR / ".env")

CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4.1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LANGS = ("en", "de", "it")
# Sections left out of search results unless nothing else is found.
BOILERPLATE = ("compliance", "warranty", "front_matter")

SPEC_PARAMS = json.loads((REPO_DIR / "shared" / "spec_parameters.json").read_text(encoding="utf-8"))["parameters"]
PARAM_BY_KEY = {p["key"]: p for p in SPEC_PARAMS}


@dataclass
class Product:
    id: str
    name: str
    kind: str                   # robot | accessory
    family: str
    aliases: list[str]
    langs: list[str]
    related: list[str]
    overview: dict
    specs: dict = field(repr=False, default_factory=dict)


@lru_cache
def client() -> OpenAI:
    return OpenAI()


def connect() -> psycopg.Connection:
    value = (os.getenv("CONNECTION_STRING") or os.getenv("DATABASE_URL") or "").strip()
    if not value:
        raise RuntimeError("Set CONNECTION_STRING in .env")
    # prepare_threshold=None: the Supabase pooler does not support prepared statements.
    conn = psycopg.connect(value, prepare_threshold=None, autocommit=True)
    register_vector(conn)
    return conn


@lru_cache
def products() -> dict[str, Product]:
    """All products, read once. The catalog is small and does not change at run time."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, kind, family, aliases, langs, related_products, overview, specs FROM products ORDER BY id"
        ).fetchall()
    return {r[0]: Product(*r) for r in rows}


# --- finding products named in a text ---------------------------------------


@lru_cache
def _alias_table() -> list[tuple[re.Pattern, str]]:
    names: list[tuple[str, str]] = []
    for p in products().values():
        for name in {p.name, p.id.replace("-", " "), *p.aliases}:
            names.append((name, p.id))
    names.sort(key=lambda x: -len(x[0]))           # "BellaBot Pro" before "BellaBot"
    table = []
    for name, pid in names:
        words = [re.escape(w) for w in re.split(r"[\s\-]+", name) if w]
        table.append((re.compile(r"(?<![\w])" + r"[\s\-]*".join(words) + r"(?![\w])", re.I), pid))
    return table


def find_products_in_text(text: str) -> list[str]:
    """Product ids named in the text. The longest name wins, so "BellaBot Pro" is not also "BellaBot"."""
    found: list[tuple[int, str]] = []
    taken: list[tuple[int, int]] = []
    for rx, pid in _alias_table():
        for m in rx.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append(m.span())
            found.append((m.start(), pid))
    return list(dict.fromkeys(pid for _, pid in sorted(found)))


# --- chunks ------------------------------------------------------------------

CHUNK_COLUMNS = ("c.id, c.product_id, c.lang, c.section_key, c.section_title, c.section_kind, "
                 "c.page, c.pdf_page, c.content, c.figures, c.seq")


def best_lang(product_id: str, lang: str | None) -> str:
    """The requested language if the manual exists in it, otherwise English."""
    return lang if lang in products()[product_id].langs else "en"


def manual_sections(conn, product_id: str, lang: str | None, include_boilerplate: bool = False) -> list[tuple]:
    return conn.execute(
        f"SELECT {CHUNK_COLUMNS}, NULL::float8 AS score FROM chunks c "
        "WHERE c.product_id = %s AND c.lang = %s AND (%s OR c.section_kind <> ALL(%s)) ORDER BY c.seq",
        (product_id, best_lang(product_id, lang), include_boilerplate, list(BOILERPLATE)),
    ).fetchall()


def embed(text: str) -> list[float]:
    return client().embeddings.create(model=EMBEDDING_MODEL, input=[text]).data[0].embedding


def vector_search(conn, query: str, product_ids: list[str] | None, lang: str | None, k: int,
                  include_boilerplate: bool = False) -> list[tuple]:
    """Closest sections by meaning. Each product is searched in the requested language,
    or in English when its manual does not exist in that language."""
    lang = lang if lang in LANGS else "en"
    return conn.execute(
        f"""
        SELECT {CHUNK_COLUMNS}, 1 - (c.embedding <=> %(v)s::vector) AS score
        FROM chunks c JOIN products p ON p.id = c.product_id
        WHERE c.embedding IS NOT NULL
          AND (%(products)s::text[] IS NULL OR c.product_id = ANY(%(products)s))
          AND (c.lang = %(lang)s OR (c.lang = 'en' AND NOT (%(lang)s = ANY(p.langs))))
          AND (%(boiler)s OR c.section_kind <> ALL(%(skip)s))
        ORDER BY c.embedding <=> %(v)s::vector
        LIMIT %(k)s
        """,
        {"v": embed(query), "products": product_ids or None, "lang": lang, "k": k,
         "boiler": include_boilerplate, "skip": list(BOILERPLATE)},
    ).fetchall()


def keyword_search(conn, query: str, product_ids: list[str] | None, lang: str | None, k: int) -> list[tuple]:
    """Sections that contain the exact words of the query (model codes, 'IP20', 'LoRa')."""
    lang = lang if lang in LANGS else "en"
    return conn.execute(
        f"""
        SELECT {CHUNK_COLUMNS}, ts_rank(c.search_tsv, q)::float8 AS score
        FROM chunks c JOIN products p ON p.id = c.product_id, plainto_tsquery('simple', %(q)s) q
        WHERE c.search_tsv @@ q
          AND (%(products)s::text[] IS NULL OR c.product_id = ANY(%(products)s))
          AND (c.lang = %(lang)s OR (c.lang = 'en' AND NOT (%(lang)s = ANY(p.langs))))
          AND c.section_kind <> ALL(%(skip)s)
        ORDER BY score DESC
        LIMIT %(k)s
        """,
        {"q": query, "products": product_ids or None, "lang": lang, "k": k, "skip": list(BOILERPLATE)},
    ).fetchall()


def spec_section(conn, product_id: str, lang: str | None) -> tuple | None:
    """The specification section of a product: in the requested language if it exists, else English."""
    for candidate in dict.fromkeys([best_lang(product_id, lang), "en"]):
        row = conn.execute(
            f"SELECT {CHUNK_COLUMNS}, NULL::float8 FROM chunks c WHERE c.product_id = %s AND c.lang = %s "
            "AND c.section_kind = 'specs' ORDER BY (c.section_key LIKE '2%%') DESC, c.seq LIMIT 1",
            (product_id, candidate)).fetchone()
        if row:
            return row
    return None
