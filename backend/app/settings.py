from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = REPO_DIR / "data"
    products_file: Path = REPO_DIR / "shared" / "products.json"
    feedback_file: Path = BACKEND_DIR / "var" / "feedback.jsonl"

    # Motore RAG: mock (incluso), python (RAG_PYTHON=modulo:funzione) o http (RAG_URL)
    rag_engine: Literal["mock", "python", "http"] = "mock"
    rag_python: str | None = None
    rag_python_search: str | None = None
    rag_url: str | None = None
    rag_search_url: str | None = None
    rag_timeout_s: float = 60.0          # attesa massima della risposta del RAG
    stream_duration_s: float = 1.5       # durata massima dell'effetto "scrittura" nel frontend

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
