"""Parser dei manuali PUDU in Markdown (data/<cartella>/<lingua>.md).

Usa solo la libreria standard, così anche il motore RAG può importarlo e
ottenere le stesse chiavi di sezione del backend.

Regole:
- una sezione inizia a ogni titolo numerato ("## 2.4 Specifications", anche "# 2.4"
  o "## 1.1Instructions"); i titoli senza numero ("## Troubles") restano dentro
  la sezione numerata che li precede;
- il testo prima del primo titolo numerato forma la sezione "0";
- se un numero compare due volte nello stesso file (succede nei manuali) la
  seconda sezione riceve la chiave "5.1~2";
- i marcatori di pagina ("*Page 3 (PDF page 4, left)*") non finiscono nel testo,
  ma danno a ogni sezione la pagina stampata e la pagina del PDF originale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

LANGS = ("en", "de", "it")

PAGE_RE = re.compile(
    r"^\*(?:(?:Page|Seite|Pagina) (\d+) \()?"
    r"(?:PDF page|PDF-Seite|pagina PDF|Pagina PDF) (\d+)"
    r"(?:, [^)*]+)?\)?\*\s*$"
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# "2.4 Titolo", "2. Titolo" oppure "1.1Titolo" (senza spazio, solo con almeno un punto)
NUMBERED_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(\S.*)$|^(\d+\.\d+(?:\.\d+)*)(?=[^\d\s.])(.+)$")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\((images/[^)\s]+)\)")
SEPARATOR_RE = re.compile(r"^-{3,}\s*$")


@dataclass
class Section:
    key: str                 # chiave unica nel file: "2.4", "5.1~2", "0"
    number: str | None       # numero stampato, None per la sezione "0"
    title: str
    level: int               # 1 per "2", 2 per "2.4", 0 per la sezione "0"
    page: int | None         # pagina stampata dove inizia
    pdf_page: int | None     # pagina del PDF multilingue originale dove inizia
    page_end: int | None = None
    lines: list[str] = field(default_factory=list)

    @property
    def markdown(self) -> str:
        return "\n".join(self.lines).strip()

    @property
    def images(self) -> list[str]:
        """Percorsi delle immagini, relativi alla cartella del manuale."""
        return list(dict.fromkeys(IMAGE_RE.findall(self.markdown)))


@dataclass
class Manual:
    lang: str
    path: Path
    meta: dict[str, str]
    sections: list[Section]

    def __post_init__(self) -> None:
        self._by_key = {s.key: s for s in self.sections}

    def get(self, key: str) -> Section | None:
        return self._by_key.get(key)

    @property
    def source_pdf(self) -> str | None:
        return self.meta.get("source_pdf")


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, text[end + 4:]


def parse_manual(path: Path, lang: str) -> Manual:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
    sections: list[Section] = []
    seen: dict[str, int] = {}
    page: int | None = None
    pdf_page: int | None = None
    current = Section(key="0", number=None, title=meta.get("title", ""), level=0, page=None, pdf_page=None)

    def has_content(s: Section) -> bool:
        return any(line.strip() for line in s.lines)

    for line in body.splitlines():
        if m := PAGE_RE.match(line):
            page = int(m.group(1)) if m.group(1) else None
            pdf_page = int(m.group(2))
            if not has_content(current):
                current.page, current.pdf_page = page, pdf_page
            current.page_end = page
            continue
        if SEPARATOR_RE.match(line):
            continue
        h = HEADING_RE.match(line)
        n = NUMBERED_RE.match(h.group(2)) if h else None
        if n:
            if current.number is not None or has_content(current):
                sections.append(current)
            number = n.group(1) or n.group(3)
            title = (n.group(2) or n.group(4)).strip()
            seen[number] = seen.get(number, 0) + 1
            key = number if seen[number] == 1 else f"{number}~{seen[number]}"
            current = Section(key=key, number=number, title=title, level=number.count(".") + 1,
                              page=page, pdf_page=pdf_page, page_end=page)
            continue
        current.lines.append(line)

    if current.number is not None or has_content(current):
        sections.append(current)
    return Manual(lang=lang, path=path, meta=meta, sections=sections)


# --- tabelle Markdown -------------------------------------------------------

_SEP_ROW_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def parse_tables(markdown: str) -> list[tuple[list[str], list[list[str]]]]:
    """Restituisce [(intestazione, righe)] per ogni tabella Markdown nel testo."""
    tables: list[tuple[list[str], list[list[str]]]] = []
    block: list[str] = []
    for line in markdown.splitlines() + [""]:
        if line.lstrip().startswith("|"):
            block.append(line)
            continue
        if len(block) >= 2 and _SEP_ROW_RE.match(block[1].strip()):
            tables.append((_cells(block[0]), [_cells(r) for r in block[2:]]))
        block = []
    return tables
