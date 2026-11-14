"""Shared settings and database connection for the ingestion scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

REPO_DIR = Path(__file__).resolve().parent.parent
load_dotenv(REPO_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR") or REPO_DIR / "data" / "PUDU-PDF-MD")
PRODUCTS_FILE = REPO_DIR / "shared" / "products.json"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536

# The Markdown parser lives in the backend so that section keys match the API.
sys.path.insert(0, str(REPO_DIR / "backend"))


def connection_string() -> str:
    value = os.getenv("CONNECTION_STRING") or os.getenv("DATABASE_URL")
    if not value:
        raise SystemExit("Set CONNECTION_STRING in .env (Postgres connection string).")
    return value.strip()


def connect(vectors: bool = True) -> psycopg.Connection:
    # prepare_threshold=None: Supabase's connection pooler does not support prepared statements.
    conn = psycopg.connect(connection_string(), prepare_threshold=None)
    if vectors:
        register_vector(conn)
    return conn
