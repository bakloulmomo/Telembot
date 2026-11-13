"""Da una fonte del RAG, in qualsiasi forma, a una citazione con link.

Il RAG non deve conoscere gli id del backend. Per ogni fonte si prova, in ordine:
- prodotto: product_id valido, altrimenti il nome della cartella o del PDF in un
  campo come source/file/path, altrimenti il testo del chunk;
- lingua: lang/language, altrimenti il nome del file (en.md, de.pdf …);
- sezione: section_id/section valido, altrimenti si cerca il testo del chunk
  dentro le sezioni dei manuali.
Ciò che non si riesce a ricavare resta vuoto: la citazione si mostra comunque.
"""

from __future__ import annotations

import re
from pathlib import PurePath

from app.catalog import Catalog
from app.manuals import LANGS, Section
from app.schemas import Citation

PATH_KEYS = ("source", "file", "file_path", "path", "filename", "file_name", "doc_id", "document", "url", "title")
SECTION_KEYS = ("section_id", "section", "section_key", "section_number")
SCORE_KEYS = ("score", "relevance_score", "similarity", "distance")
_LANG_FILE_RE = re.compile(r"(?:^|[/\\_.-])(en|de|it)\.(?:md|pdf)$", re.I)
_WS_RE = re.compile(r"\s+")
MAX_TEXT = 1500


def _norm(text: str) -> str:
    return _WS_RE.sub(" ", text).strip().lower()


class CitationResolver:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        # (prodotto, lingua, sezione, testo normalizzato) per cercare i chunk per contenuto
        self._index = [(pid, lang, s, _norm(s.markdown))
                       for pid, d in catalog.by_id.items() for lang, m in d.manuals.items() for s in m.sections]
        # cartelle e nomi dei PDF, dal più lungo, per riconoscere il prodotto da un percorso
        names = []
        for pid, d in catalog.by_id.items():
            names.append((PurePath(d.product.folder).name.lower(), pid))
            for m in d.manuals.values():
                if m.source_pdf:
                    names.append((PurePath(m.source_pdf).stem.lower(), pid))
        self._path_names = sorted(set(names), key=lambda x: -len(x[0]))

    # --- singoli campi ---------------------------------------------------------

    def _product(self, src: dict) -> str | None:
        pid = str(src.get("product_id") or "").lower()
        if pid in self.catalog.by_id:
            return pid
        for key in ("product", "product_name"):
            value = str(src.get(key) or "").lower()
            for p in self.catalog.products:
                if value in (p.id, p.name.lower()):
                    return p.id
        for key in PATH_KEYS:
            value = str(src.get(key) or "").lower()
            for name, pid in self._path_names:
                if name and name in value:
                    return pid
        return None

    @staticmethod
    def _lang(src: dict) -> str | None:
        value = str(src.get("lang") or src.get("language") or "").lower()[:2]
        if value in LANGS:
            return value
        for key in PATH_KEYS:
            if m := _LANG_FILE_RE.search(str(src.get(key) or "")):
                return m.group(1).lower()
        return None

    def _by_text(self, text: str, pid: str | None, lang: str | None) -> tuple[str, str, Section] | None:
        """Sezione che contiene il testo del chunk.

        Prima cerca il testo intero; se il chunk attraversa più sezioni, conta quanti
        pezzi da 60 caratteri compaiono in ciascuna. Robot simili condividono righe
        identiche: se il miglior risultato è conteso tra prodotti diversi non sceglie,
        perché una citazione senza link è meglio di un link al robot sbagliato.
        """
        norm = _norm(text)
        if len(norm) < 25:
            return None
        candidates = [c for c in self._index if (not pid or c[0] == pid) and (not lang or c[1] == lang)]
        best = [c for c in candidates if norm in c[3]]
        if not best:
            size = min(60, len(norm))
            step = max(size, (len(norm) - size) // 7)
            probes = [norm[i:i + size] for i in range(0, len(norm) - size + 1, step)]
            scored = [(sum(p in c[3] for p in probes), c) for c in candidates]
            top = max((s for s, _ in scored), default=0)
            best = [c for s, c in scored if s == top] if top else []
        if not best or len({c[0] for c in best}) > 1:
            return None
        p_id, lg, section, _ = best[0]
        return p_id, lg, section

    @staticmethod
    def _score(src: dict) -> float | None:
        for key in SCORE_KEYS:
            try:
                return round(float(src[key]), 4)
            except (KeyError, TypeError, ValueError):
                continue
        return None

    # --- risultato -------------------------------------------------------------

    def resolve(self, src: dict, n: int) -> Citation:
        text = str(src.get("text") or "")
        pid, lang = self._product(src), self._lang(src)
        section: Section | None = None

        if pid:
            manual = self.catalog.by_id[pid].manuals.get(lang or "en")
            for key in SECTION_KEYS:
                if manual and src.get(key) is not None and (section := manual.get(str(src[key]))):
                    lang = manual.lang
                    break
        if section is None and text:
            found = self._by_text(text, pid, lang) or (self._by_text(text, pid, None) if lang else None)
            if found:
                pid, lang, section = found

        data = self.catalog.get(pid) if pid else None
        manual = data.manuals.get(lang or "en") if data else None
        page = src.get("page")
        label = self._label(src, data, section, n)
        return Citation(
            n=n,
            label=label,
            text=text[:MAX_TEXT],
            product_id=pid,
            product_name=data.product.name if data else None,
            lang=manual.lang if manual else None,
            section_id=section.key if section else None,
            section_title=section.title if section else None,
            page=section.page if section else (page if isinstance(page, int) else None),
            score=self._score(src),
            source_url=self.catalog.source_url(pid, manual.lang, section.key) if section and manual else None,
            pdf_url=self.catalog.pdf_url(pid, manual, section.pdf_page if section else None) if manual else None,
            image_urls=[self.catalog.file_url(pid, img) for img in section.images] if section else [],
        )

    @staticmethod
    def _label(src: dict, data, section: Section | None, n: int) -> str:
        if data and section:
            number = f"{section.number} " if section.number else ""
            return f"{data.product.name} · {number}{section.title}".strip()
        if data:
            return data.product.name
        for key in PATH_KEYS:
            if src.get(key):
                return PurePath(str(src[key])).name
        return f"Fonte {n}"
