"""Motore RAG finto, per sviluppare frontend e backend senza aspettare quello reale.

Cerca per parole chiave (un BM25 semplificato) nelle sezioni dei manuali e
risponde con un testo di prova che elenca le sezioni trovate.
Non usa LLM e non capisce domande in una lingua diversa dalla fonte.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from app.catalog import Catalog
from app.rag import RagResult

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_FIGURE_LINE_RE = re.compile(r"^\s*(!\[|>|\*(Labels|Beschriftungen|Etichette))")

_STOPWORDS = {
    "it": {"il", "lo", "la", "le", "gli", "di", "che", "è", "come", "quale", "quali", "per", "del", "della",
           "un", "una", "quanto", "quanti", "qual", "sono", "cosa", "non", "con", "nel", "nella", "si", "mio"},
    "de": {"der", "die", "das", "ist", "wie", "welche", "welcher", "und", "nicht", "mit", "ein", "eine", "für",
           "was", "den", "dem", "von", "kann", "ich", "wird", "sind", "hat"},
    "en": {"the", "is", "what", "which", "how", "of", "and", "to", "a", "an", "for", "does", "can", "with",
           "my", "are", "do", "it", "in", "on"},
}
_ALL_STOPWORDS = set().union(*_STOPWORDS.values())

_TEXTS = {
    "it": {"intro": "Risposta di prova: il motore RAG non è ancora collegato. Queste sono le sezioni dei manuali "
                    "più vicine alla domanda:\n\n",
           "none": "Risposta di prova: non ho trovato nei manuali sezioni che corrispondano alla domanda."},
    "en": {"intro": "Test answer: the RAG engine is not connected yet. These are the manual sections closest "
                    "to the question:\n\n",
           "none": "Test answer: I found no manual sections matching the question."},
    "de": {"intro": "Testantwort: Die RAG-Engine ist noch nicht verbunden. Diese Handbuchabschnitte passen am "
                    "besten zur Frage:\n\n",
           "none": "Testantwort: Ich habe keine passenden Abschnitte in den Handbüchern gefunden."},
}


def _tokens(text: str) -> list[str]:
    return [t for t in _WORD_RE.findall(text.lower()) if len(t) > 1]


def detect_lang(text: str) -> str:
    words = _tokens(text)
    scores = {lang: sum(w in sw for w in words) for lang, sw in _STOPWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "en"


class MockRag:
    name = "mock"

    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.chunks: list[dict] = []
        self._tf: list[Counter] = []
        self._len: list[int] = []
        self._joined: list[str] = []     # " tok tok … " per riconoscere le coppie di parole
        for pid, data in catalog.by_id.items():
            for lang, manual in data.manuals.items():
                for s in manual.sections:
                    text = "\n".join(line for line in s.markdown.splitlines() if not _FIGURE_LINE_RE.match(line))
                    chunk = {"product_id": pid, "lang": lang, "section_id": s.key, "text": text.strip()}
                    toks = _tokens(f"{data.product.name} {s.title} {text}")
                    self.chunks.append(chunk)
                    self._tf.append(Counter(toks))
                    self._len.append(len(toks))
                    self._joined.append(f" {' '.join(toks)} ")
        df = Counter(t for tf in self._tf for t in tf)
        n = len(self.chunks)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self._avglen = sum(self._len) / max(n, 1)
        # alias dei nomi, dal più lungo: "kettybot pro" prima di "kettybot"
        aliases = {}
        for pid, data in catalog.by_id.items():
            aliases[data.product.name.lower()] = pid
            aliases[pid.replace("-", " ")] = pid
        self._aliases = sorted(aliases.items(), key=lambda kv: -len(kv[0]))

    def detect_products(self, text: str) -> list[str]:
        found: list[str] = []
        low = f" {text.lower()} "
        for alias, pid in self._aliases:
            pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
            if re.search(pattern, low):
                if pid not in found:
                    found.append(pid)
                low = re.sub(pattern, " ", low)
        return found

    async def search(self, query: str, product_ids: list[str], lang: str | None, k: int = 8) -> list[dict]:
        q_terms = [t for t in dict.fromkeys(_tokens(query)) if t not in _ALL_STOPWORDS] or _tokens(query)
        bigrams = [(a, b) for a, b in zip(q_terms, q_terms[1:])]
        allowed = set(product_ids)
        scored: list[tuple[float, int]] = []
        for i, chunk in enumerate(self.chunks):
            if allowed and chunk["product_id"] not in allowed:
                continue
            if lang:
                langs = self.catalog.by_id[chunk["product_id"]].manuals
                if chunk["lang"] != (lang if lang in langs else "en"):
                    continue
            tf, length = self._tf[i], self._len[i]
            score = 0.0
            for t in q_terms:
                f = tf.get(t, 0)
                if f:
                    score += self._idf[t] * f * 2.2 / (f + 1.2 * (0.5 + 0.5 * length / self._avglen))
            for a, b in bigrams:      # bonus se due parole della domanda compaiono di seguito
                if f" {a} {b} " in self._joined[i]:
                    score += self._idf.get(a, 0) + self._idf.get(b, 0)
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)

        results: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for score, i in scored:
            chunk = self.chunks[i]
            key = (chunk["product_id"], chunk["section_id"])
            if lang is None and key in seen:      # senza lingua: una sola versione per sezione
                continue
            seen.add(key)
            results.append({**chunk, "score": round(score, 3)})
            if len(results) == k:
                break
        return results

    async def ask(self, question: str, history: list[dict], lang: str | None, product_ids: list[str]) -> RagResult:
        lang = lang or detect_lang(question)
        products = product_ids or self.detect_products(question)
        hits = await self.search(question, products, lang, k=3)
        names = {pid: d.product.name for pid, d in self.catalog.by_id.items()}
        if hits:
            parts = [_TEXTS[lang]["intro"]]
            for i, h in enumerate(hits, start=1):
                snippet = re.sub(r"\s+", " ", h["text"])[:220].strip()
                parts.append(f"- **{names[h['product_id']]} § {h['section_id']}** [{i}]: {snippet}…\n")
            answer = "".join(parts)
        else:
            answer = _TEXTS[lang]["none"]
        return RagResult(answer=answer, sources=hits)
