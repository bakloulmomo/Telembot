"""Checks on a generated answer. Plain code, no LLM call."""

from __future__ import annotations

import re

CITATION_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?")
STATUS_TAG_RE = re.compile(r"\s*\[(?:not_in_docs|answered|needs_clarification)\]")
SPACE_BEFORE_PUNCTUATION_RE = re.compile(r"[ \t]+([.,;:])")


def cited_numbers(answer: str) -> list[int]:
    """Source numbers used in the answer, in order of first appearance."""
    out: list[int] = []
    for group in CITATION_RE.findall(answer):
        for n in re.split(r"\s*,\s*", group):
            if int(n) not in out:
                out.append(int(n))
    return out


def renumber(answer: str, mapping: dict[int, int]) -> str:
    """Rewrite [n] markers with new numbers; markers for unknown sources are removed."""
    def repl(m: re.Match) -> str:
        kept = [str(mapping[int(n)]) for n in re.split(r"\s*,\s*", m.group(1)) if int(n) in mapping]
        return "".join(f"[{n}]" for n in dict.fromkeys(kept))
    return SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", CITATION_RE.sub(repl, answer))


def strip_tags(answer: str) -> str:
    """Remove bracketed status words the model sometimes adds, such as "[not_in_docs]"."""
    return SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", STATUS_TAG_RE.sub("", answer)).strip()


def _numbers(text: str) -> set[str]:
    out = set()
    for raw in NUMBER_RE.findall(text):
        value = raw.replace(",", ".")
        out.add(value)
        if "." in value:
            out.add(value.rstrip("0").rstrip("."))
    return out


def audit_numbers(answer: str, cited_sources: list[dict], question: str = "") -> dict:
    """Classify every number in the answer (including 0-12) against cited sources.

    Citation markers ([1], [2]) are ignored. "25,6" and "25.6" count as the same number.
    Returns {"verified": [{"value": ..., "sources": [1, ...]}], "from_question": [...], "unverified": [...]}.
    """
    text = CITATION_RE.sub(" ", answer)
    q_nums = _numbers(question)
    source_nums = {i: _numbers(s.get("text", "")) for i, s in enumerate(cited_sources, start=1)}

    verified: list[dict] = []
    seen_verified: set[str] = set()
    from_question: list[str] = []
    unverified: list[str] = []

    for raw in NUMBER_RE.findall(text):
        value = raw.replace(",", ".")
        short = value.rstrip("0").rstrip(".") if "." in value else value
        matched = [i for i, nums in source_nums.items() if value in nums or short in nums]
        if matched:
            if raw not in seen_verified:
                seen_verified.add(raw)
                verified.append({"value": raw, "sources": matched})
        elif value in q_nums or short in q_nums:
            if raw not in from_question:
                from_question.append(raw)
        else:
            if raw not in unverified:
                unverified.append(raw)

    return {"verified": verified, "from_question": from_question, "unverified": unverified}
