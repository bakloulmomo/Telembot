"""Collegamento al motore RAG: il contratto minimo.

Un motore RAG, qualunque sia, riceve una domanda e restituisce una risposta con le
sue fonti. Il backend accetta i formati più comuni e normalizza tutto qui:

    "solo il testo della risposta"
    {"answer": "…", "sources": [...]}            (anche "response"/"output"/"result",
                                                  "source_documents"/"documents"/"context"…)
    ("testo", [fonti])
    oggetti LangChain / LlamaIndex (Document, Response, NodeWithScore)

Una fonte può essere una stringa o un oggetto con il testo del chunk
("text"/"page_content"/"content") ed eventuali metadati, anche annidati in
"metadata": file, product_id, lang, section_id, page, score. Nessuno è
obbligatorio: app/citations.py ritrova prodotto e sezione anche dal solo testo.

Tre modi di collegare un motore (RAG_ENGINE nel file .env):
    mock    motore finto incluso, per sviluppare senza il RAG
    python  una funzione Python, es. RAG_PYTHON=rag.pipeline:answer
    http    un servizio qualsiasi, es. RAG_URL=http://localhost:9000/ask
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.settings import Settings

ANSWER_KEYS = ("answer", "response", "output", "result", "text", "content")
SOURCES_KEYS = ("sources", "source_documents", "source_nodes", "documents", "context", "citations", "results")
TEXT_KEYS = ("text", "page_content", "content", "chunk", "snippet")


@dataclass
class RagResult:
    answer: str
    sources: list[dict] = field(default_factory=list)
    status: str | None = None       # answered | not_in_docs | needs_clarification, se il motore lo fornisce
    language: str | None = None     # lingua della risposta, se il motore la fornisce
    gaps: list[str] = field(default_factory=list)     # parti della domanda che i manuali non coprono
    options: list[str] = field(default_factory=list)  # scelte proposte quando status = needs_clarification


def _first(d: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return None


def _as_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        d = dict(obj)
    elif hasattr(obj, "model_dump"):
        d = obj.model_dump()
    else:
        d = {k: getattr(obj, k) for k in (*ANSWER_KEYS, *SOURCES_KEYS, "page_content", "metadata", "score", "node")
             if hasattr(obj, k) and not callable(getattr(obj, k))}
    node = d.pop("node", None)               # LlamaIndex NodeWithScore
    if node is not None:
        d = {**_as_dict(node), **{k: v for k, v in d.items() if v is not None}}
    return d


def normalize_source(src: Any) -> dict:
    if isinstance(src, str):
        return {"text": src}
    d = _as_dict(src)
    meta = d.pop("metadata", None) or {}
    flat = {**(meta if isinstance(meta, dict) else {}), **d}
    flat["text"] = str(_first(flat, TEXT_KEYS) or "")
    return flat


def normalize_result(raw: Any) -> RagResult:
    if isinstance(raw, str):
        return RagResult(answer=raw)
    if isinstance(raw, (tuple, list)) and len(raw) == 2 and isinstance(raw[0], str):
        answer, sources = raw
    else:
        d = _as_dict(raw)
        answer, sources = _first(d, ANSWER_KEYS), _first(d, SOURCES_KEYS)
    if isinstance(sources, (str, dict)):
        sources = [sources]
    extra = raw if isinstance(raw, dict) else {}
    return RagResult(answer=str(answer or ""), sources=[normalize_source(s) for s in (sources or [])],
                     status=extra.get("status") or None, language=extra.get("language") or None,
                     gaps=[str(g) for g in extra.get("gaps") or [] if g],
                     options=[str(o) for o in extra.get("options") or [] if o])


def normalize_sources(raw: Any) -> list[dict]:
    """Per la ricerca: accetta una lista di fonti oppure un oggetto che la contiene."""
    if isinstance(raw, list):
        return [normalize_source(s) for s in raw]
    return normalize_result(raw).sources


def create_engine(settings: Settings, catalog):
    if settings.rag_engine == "python":
        from app.rag.adapters import PythonRag
        if not settings.rag_python:
            raise RuntimeError("RAG_ENGINE=python richiede RAG_PYTHON=modulo:funzione nel file .env")
        return PythonRag(settings.rag_python, settings.rag_python_search)
    if settings.rag_engine == "http":
        from app.rag.adapters import HttpRag
        if not settings.rag_url:
            raise RuntimeError("RAG_ENGINE=http richiede RAG_URL nel file .env")
        return HttpRag(settings.rag_url, settings.rag_search_url, timeout_s=settings.rag_timeout_s)
    from app.rag.mock import MockRag
    return MockRag(catalog)
