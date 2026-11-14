"""Da una fonte del RAG, in qualsiasi forma, a una citazione con link.

Il RAG non deve conoscere gli id del backend. Per ogni fonte si prova, in ordine:
- prodotto: product_id valido, altrimenti il nome della cartella o del PDF in un
  campo come source/file/path, altrimenti il testo del chunk;
- lingua: lang/language, altrimenti il nome del file (en.md, de.pdf …);
- sezione: section_id/section valido, poi il numero o il titolo in section_title
  ("2.4 Specifications"), altrimenti si cerca il testo del chunk dentro le
  sezioni dei manuali.
- immagini: le figure scelte dal RAG (figures, con la legenda), poi image_paths
  della fonte, altrimenti tutte quelle della sezione.
Ciò che non si riesce a ricavare resta vuoto: la citazione si mostra comunque.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePath

from app.catalog import Catalog
from app.manuals import LANGS, NUMBERED_RE, Section
from app.schemas import Citation, Figure, FigureLabel

PATH_KEYS = ("source", "file", "file_path", "path", "filename", "file_name", "doc_id", "document", "url", "title")
PRODUCT_KEYS = ("product_id", "product_slug", "slug", "product", "product_name")
SECTION_KEYS = ("section_id", "section", "section_key", "section_number")
SECTION_TITLE_KEYS = ("section_title", "heading", "section_name")
IMAGE_KEYS = ("image_paths", "images", "image_path", "image")
SCORE_KEYS = ("score", "relevance_score", "similarity", "distance")
_LANG_FILE_RE = re.compile(r"(?:^|[/\\_.-])(en|de|it)\.(?:md|pdf)$", re.I)
_PAGE_RE = re.compile(r"\d+")
_WS_RE = re.compile(r"\s+")
MAX_TEXT = 1500
MAX_SECTION_TEXT = 6000
_FIG_PAGE_RE = re.compile(r"-p0*(\d+)[LR]?-fig", re.I)
_AI_NOTE_RE = re.compile(r"^>\s*\*?(Figure description|Abbildungsbeschreibung|Descrizione della figura)", re.I)
_LEGEND_RE = re.compile(r"^\*(Labels|Beschriftungen|Etichette):?\*:?$", re.I)


def figure_pdf_page(path: str) -> int | None:
    """images/en-p004R-fig02.png → 4"""
    m = _FIG_PAGE_RE.search(path)
    return int(m.group(1)) if m else None


def section_path(manual, section: Section) -> str:
    """"1. Safety instructions › 1.1 Power usage" """
    own = f"{section.number} {section.title}" if section.number else section.title
    if section.number and "." in section.number:
        parent = manual.get(section.number.rsplit(".", 1)[0])
        if parent:
            return f"{parent.number}. {parent.title} › {own}"
    return f"{section.number}. {section.title}" if section.number else own


def manual_text(markdown: str) -> str:
    """Il testo della sezione come stampato nel manuale: senza immagini, senza le descrizioni
    delle figure scritte dall'AI e senza grassetti. La legenda di una figura resta solo se la
    sezione non ha altro testo (un elenco di parti come "5 Lidar")."""
    lines, legend, in_legend = [], [], False
    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("![") or _AI_NOTE_RE.match(line):
            continue
        if _LEGEND_RE.match(line):
            in_legend = True
            continue
        if in_legend and line.startswith(("- ", "* ")):
            legend.append(line.replace("**", ""))
            continue
        if line:
            in_legend = False
        lines.append(raw.replace("**", ""))
    text = "\n".join(lines).strip()
    has_text = any(l.strip() and not l.lstrip().startswith("#") for l in lines)
    return text if has_text else "\n".join([text, *legend]).strip()


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
        # id, slug ("bellabot_pro" vale come "bellabot-pro") o nome del prodotto
        for key in PRODUCT_KEYS:
            value = str(src.get(key) or "").strip().lower()
            if not value:
                continue
            slug = re.sub(r"[\s_]+", "-", value)
            for p in self.catalog.products:
                if slug == p.id or value == p.name.lower():
                    return p.id
        # nome della cartella o del PDF in un percorso, anche quello di un'immagine
        values = [str(src.get(key) or "") for key in PATH_KEYS] + self._image_values(src)
        for value in map(str.lower, values):
            for name, pid in self._path_names:
                if name and name in value:
                    return pid
        return None

    @staticmethod
    def _image_values(src: dict) -> list[str]:
        values = []
        for key in IMAGE_KEYS:
            v = src.get(key)
            values += [str(x) for x in v if x] if isinstance(v, (list, tuple)) else ([str(v)] if v else [])
        return values

    def _images(self, src: dict, pid: str) -> list[str]:
        """Percorsi delle immagini della fonte → URL, solo se il file esiste nella cartella del prodotto.

        Accetta "images/x.png", "manuals/<cartella>/images/x.png" o un percorso assoluto.
        """
        root = self.catalog.by_id[pid].product.path.resolve()
        urls = []
        for value in self._image_values(src):
            value = value.replace("\\", "/")
            idx = value.lower().rfind("images/")
            candidates = [value[idx:]] if idx >= 0 else []
            candidates.append(value)
            for rel in candidates:
                target = (root / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
                if target.is_relative_to(root) and target.is_file():
                    url = self.catalog.file_url(pid, target.relative_to(root).as_posix())
                    if url not in urls:
                        urls.append(url)
                    break
        return urls

    @staticmethod
    def _section_by_title(manual, src: dict) -> Section | None:
        """"2.4 Specifications" → sezione 2.4; senza numero, il titolo esatto."""
        for key in SECTION_TITLE_KEYS:
            title = _WS_RE.sub(" ", str(src.get(key) or "").replace(" ", " ")).strip()
            if not title:
                continue
            m = NUMBERED_RE.match(title)
            number = (m.group(1) or m.group(3)) if m else None
            if number and (section := manual.get(number)):
                return section
            name = _norm((m.group(2) or m.group(4)) if m else title)
            matches = [s for s in manual.sections if _norm(s.title) == name]
            if len(matches) == 1:
                return matches[0]
        return None

    @staticmethod
    def _page(src: dict) -> int | None:
        """page come numero, oppure il primo numero di un'etichetta "Page 2 (PDF page 3, right)"."""
        for key in ("page", "page_number", "page_label"):
            value = src.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
            if isinstance(value, str) and (m := _PAGE_RE.search(value)):
                return int(m.group())
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
                    break
            if section is None and manual:
                section = self._section_by_title(manual, src)
            if section is not None:
                lang = manual.lang
        if section is None and text:
            found = self._by_text(text, pid, lang) or (self._by_text(text, pid, None) if lang else None)
            if found:
                pid, lang, section = found

        data = self.catalog.get(pid) if pid else None
        manual = data.manuals.get(lang or "en") if data else None
        label = self._label(src, data, section, n)
        # immagini: prima le figure scelte dal RAG (con la legenda), poi gli image_paths
        # della fonte, altrimenti tutte quelle della sezione
        figures = self._figures(src, pid, section)
        if figures is not None:
            images = [f.url for f in figures]
        else:
            images = self._images(src, pid) if pid else []
            if not images and section:
                images = [self.catalog.file_url(pid, img) for img in section.images]
        return Citation(
            n=n,
            label=label,
            # il testo del manuale per la "foto" della pagina nel pannello; il chunk del RAG se la sezione è ignota
            text=manual_text(section.markdown)[:MAX_SECTION_TEXT] if section else text[:MAX_TEXT],
            product_id=pid,
            product_name=data.product.name if data else None,
            category=data.product.category if data else None,
            document=(manual.meta.get("title") or f"{data.product.name} User Manual") if manual else None,
            lang=manual.lang if manual else None,
            section_id=section.key if section else None,
            section_title=section.title if section else None,
            section_path=section_path(manual, section) if section and manual else None,
            page=section.page if section else self._page(src),
            pdf_page=section.pdf_page if section else None,
            page_side=section.pdf_side if section else None,
            pdf_file=manual.source_pdf if manual else None,
            score=self._score(src),
            source_url=self.catalog.source_url(pid, manual.lang, section.key) if section and manual else None,
            pdf_url=self.catalog.pdf_url(pid, manual, section.pdf_page if section else None) if manual else None,
            image_urls=images,
            figures=figures or [],
            note=str(src["note"])[:1000] if src.get("note") else None,
        )

    def _figures(self, src: dict, pid: str | None, section: Section | None = None) -> list[Figure] | None:
        """Figure scelte dal RAG per questa fonte.

        None se il RAG non dice nulla sulle figure (in quel caso si mostrano tutte
        le immagini della sezione, come prima); una lista, anche vuota, se lo dice.
        """
        raw = src.get("figures")
        if raw is None or not isinstance(raw, list):
            return None
        out: list[Figure] = []
        for item in raw:
            path = item.get("path") if isinstance(item, dict) else item
            if not pid or not isinstance(path, str) or not path.startswith("images/"):
                continue
            item = item if isinstance(item, dict) else {}
            labels = [FigureLabel(n=(str(l["n"]) if l.get("n") is not None else None), text=str(l.get("text", "")))
                      for l in item.get("labels") or [] if isinstance(l, dict)]
            pdf_page = figure_pdf_page(path)
            where = f"{section.number} {section.title}" if section and section.number else (section.title if section else "")
            caption = ", ".join(x for x in (where, f"PDF page {pdf_page}" if pdf_page else "") if x) or None
            out.append(Figure(id=item.get("id"), url=self.catalog.file_url(pid, path), caption=caption,
                              page=pdf_page, labels=labels, description=item.get("caption")))
        return out

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
