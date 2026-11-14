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


def unsupported_numbers(answer: str, evidence_text: str, question: str = "") -> list[str]:
    """Numbers in the answer that appear neither in the evidence nor in the question.

    Citation markers are ignored. "25,6" and "25.6" count as the same number.
    Small counts (0-12) are allowed without evidence: they are usually the model
    counting items ("two robots", "3 steps").
    """
    text = CITATION_RE.sub(" ", answer)
    known = _numbers(evidence_text) | _numbers(question)
    missing = []
    for raw in NUMBER_RE.findall(text):
        value = raw.replace(",", ".")
        short = value.rstrip("0").rstrip(".") if "." in value else value
        if value in known or short in known:
            continue
        if re.fullmatch(r"\d+", value) and int(value) <= 12:
            continue
        if raw not in missing:
            missing.append(raw)
    return missing


def count_numbers(answer: str) -> int:
    """How many numeric values the answer states (citation markers not counted)."""
    return len(NUMBER_RE.findall(CITATION_RE.sub(" ", answer)))
