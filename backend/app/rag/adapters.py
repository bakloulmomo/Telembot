"""Adattatori per collegare un motore RAG senza scrivere codice nel backend.

Ogni motore espone:
    async ask(question, history, lang, product_ids) -> RagResult        obbligatorio
    async search(query, product_ids, lang, k) -> list[dict]             facoltativo
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
from typing import Any, Callable

import httpx

from app.rag import RagResult, normalize_result, normalize_sources
from app.settings import REPO_DIR


def _load(target: str) -> Callable:
    """"modulo.sotto:funzione" → funzione. La radice del progetto è nel path, quindi `rag.…` funziona."""
    if str(REPO_DIR) not in sys.path:
        sys.path.insert(0, str(REPO_DIR))
    module_name, _, func_name = target.partition(":")
    if not func_name:
        raise RuntimeError(f"Formato non valido: {target!r}. Usa modulo:funzione, es. rag.pipeline:answer")
    return getattr(importlib.import_module(module_name), func_name)


async def _call(func: Callable, first: str, **kwargs: Any) -> Any:
    """Chiama la funzione passando solo gli argomenti che accetta; il primo è sempre la domanda."""
    params = inspect.signature(func).parameters
    accepts_all = any(p.kind is p.VAR_KEYWORD for p in params.values())
    names = list(params)
    kwargs = {k: v for k, v in kwargs.items() if accepts_all or (k in params and k != names[0])}
    if inspect.iscoroutinefunction(func):
        return await func(first, **kwargs)
    result = await asyncio.to_thread(func, first, **kwargs)
    return await result if inspect.isawaitable(result) else result


class PythonRag:
    """RAG_ENGINE=python: chiama una funzione, sincrona o asincrona.

    Basta anche `def answer(question): return "testo"`. Se la funzione ha parametri
    chiamati history, lang, product_ids (o **kwargs) li riceve.
    """

    name = "python"

    def __init__(self, target: str, search_target: str | None = None):
        self._answer = _load(target)
        self._search = _load(search_target) if search_target else None
        if self._search is None:
            self.search = None

    async def ask(self, question: str, history: list[dict], lang: str | None, product_ids: list[str],
                  progress: Callable[[dict], None] | None = None) -> RagResult:
        """`progress` riceve eventi {"step", "detail"} mentre il motore lavora, se la funzione lo accetta."""
        raw = await _call(self._answer, question, history=history, lang=lang, product_ids=product_ids,
                          progress=progress)
        return normalize_result(raw)

    async def search(self, query: str, product_ids: list[str], lang: str | None, k: int) -> list[dict]:
        raw = await _call(self._search, query, product_ids=product_ids, lang=lang, k=k)
        return normalize_sources(raw)[:k]


class HttpRag:
    """RAG_ENGINE=http: il motore è un servizio a parte, in qualsiasi linguaggio.

    Riceve   POST RAG_URL         {"question", "history", "lang", "product_ids"}
    Risponde JSON in uno dei formati accettati da normalize_result.
    Ricerca facoltativa: POST RAG_SEARCH_URL {"query", "product_ids", "lang", "k"}.
    """

    name = "http"

    def __init__(self, url: str, search_url: str | None = None, timeout_s: float = 60,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.url = url
        self.search_url = search_url
        self.client = httpx.AsyncClient(timeout=timeout_s, transport=transport)
        if not search_url:
            self.search = None

    async def ask(self, question: str, history: list[dict], lang: str | None, product_ids: list[str]) -> RagResult:
        r = await self.client.post(self.url, json={"question": question, "history": history, "lang": lang,
                                                   "product_ids": product_ids})
        r.raise_for_status()
        return normalize_result(r.json() if "json" in r.headers.get("content-type", "") else r.text)

    async def search(self, query: str, product_ids: list[str], lang: str | None, k: int) -> list[dict]:
        r = await self.client.post(self.search_url, json={"query": query, "product_ids": product_ids,
                                                          "lang": lang, "k": k})
        r.raise_for_status()
        return normalize_sources(r.json())[:k]
