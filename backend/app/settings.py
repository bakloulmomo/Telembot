from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Il .env della radice (quello del motore RAG, con OPENAI_API_KEY) e poi backend/.env, che ha la precedenza
    model_config = SettingsConfigDict(env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"), env_file_encoding="utf-8",
                                      extra="ignore")

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

    # Domande a voce (POST /api/transcribe). Senza chiave il frontend usa il riconoscimento del browser.
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    transcribe_model: str = "gpt-4o-mini-transcribe"
    transcribe_max_mb: float = 10.0

    cors_origins: list[str] =["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("data_dir", "products_file", "feedback_file")
    @classmethod
    def _relative_to_backend(cls, value: Path) -> Path:
        """Un percorso relativo nel file .env vale rispetto a backend/, da qualunque cartella si avvii il server."""
        return value if value.is_absolute() else (BACKEND_DIR / value).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
