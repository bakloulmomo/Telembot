"""The three retrieval tools and the evidence they collect.

Every tool adds numbered sources to one Evidence object and returns the text the
model reads. The model can only cite source numbers and figure ids that are in it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import store

IMAGE_RE = re.compile(r"!\[[^\]]*\]\((images/[^)\s]+)\)")
MAX_WHOLE_MANUALS = 2          # with more products than this, search instead of reading whole manuals
RELATED_K = 4                  # sections taken from each search over related products
SEARCH_K = 8


@dataclass
class Source:
    n: int
    product_id: str
    lang: str
    section_id: str
    title: str
    page: int | None
    pdf_page: int | None
    text: str                  # what the model reads
    figures: list[dict] = field(default_factory=list)
    score: float | None = None
    kind: str = "section"      # section | specs


@dataclass
class Evidence:
    sources: list[Source] = field(default_factory=list)
    _index: dict[tuple, int] = field(default_factory=dict)

    def add(self, key: tuple, **fields) -> Source:
        """Add a source once. Asking for the same section again returns the same number."""
        if key in self._index:
            return self.sources[self._index[key]]
        source = Source(n=len(self.sources) + 1, **fields)
        self._index[key] = len(self.sources)
        self.sources.append(source)
        return source

    @property
    def figure_ids(self) -> set[str]:
        return {f["id"] for s in self.sources for f in s.figures}

    def text(self) -> str:
        return "\n".join(s.text for s in self.sources)


def _name(product_id: str) -> str:
    return store.products()[product_id].name


def _add_chunk(evidence: Evidence, row: tuple) -> Source:
    _id, pid, lang, key, title, _kind, page, pdf_page, content, figures, _seq, score = row
    by_path = {f["path"]: f for f in figures}
    # Show the model where each figure sits in the text, by id instead of by file path.
    text = IMAGE_RE.sub(lambda m: f"[FIGURE {by_path[m.group(1)]['id']}]" if m.group(1) in by_path else "", content)
    return evidence.add(("chunk", pid, lang, key), product_id=pid, lang=lang, section_id=key, title=title or "",
                        page=page, pdf_page=pdf_page, text=text, figures=figures, score=score)


def _render(sources: list[Source]) -> str:
    if not sources:
        return "No sections found."
    out = []
    for s in sources:
        out.append(f"[{s.n}] {_name(s.product_id)} · {s.section_id} {s.title} · page {s.page} · language {s.lang}\n{s.text}")
    return "\n\n-----\n\n".join(out)


def _check_products(product_ids: list[str] | None) -> list[str]:
    catalog = store.products()
    unknown = [p for p in product_ids or [] if p not in catalog]
    if unknown:
        raise ValueError(f"Unknown product ids {unknown}. Valid ids: {', '.join(catalog)}")
    return list(dict.fromkeys(product_ids or []))


# --- tool 1 ------------------------------------------------------------------


def search_manuals(evidence: Evidence, conn, query: str, product_ids: list[str] | None = None,
                   lang: str | None = None) -> str:
    product_ids = _check_products(product_ids)
    lang = lang if lang in store.LANGS else "en"
    found: list[Source] = []

    if product_ids and len(product_ids) <= MAX_WHOLE_MANUALS:
        # The product is known: read its whole manual. One manual is only 3-8k tokens,
        # and this avoids picking the wrong section or the wrong model.
        for pid in product_ids:
            found += [_add_chunk(evidence, r) for r in store.manual_sections(conn, pid, lang)]
        related = [r for pid in product_ids for r in store.products()[pid].related if r not in product_ids]
        if related:
            found += [_add_chunk(evidence, r)
                      for r in store.vector_search(conn, query, list(dict.fromkeys(related)), lang, RELATED_K)]
    else:
        # No product, or many: closest sections by meaning plus exact-word matches.
        rows = store.vector_search(conn, query, product_ids or None, lang, SEARCH_K)
        seen = {r[0] for r in rows}
        rows += [r for r in store.keyword_search(conn, query, product_ids or None, lang, 4) if r[0] not in seen]
        found = [_add_chunk(evidence, r) for r in rows]

    found = list({s.n: s for s in found}.values())
    return _render(found)


# --- tools 2 and 3 -----------------------------------------------------------


def _spec_source(evidence: Evidence, conn, product_id: str, lang: str | None) -> Source | None:
    """One source per product for its specification table. The cited section is in the
    user's language when that manual exists; the values themselves come from the English manual."""
    specs = store.products()[product_id].specs
    row = store.spec_section(conn, product_id, lang)
    if row is None or not specs:
        return None
    _id, pid, row_lang, key, title, _kind, page, pdf_page, _content, _figures, _seq, _score = row
    lines = []
    for param_key, entries in specs.items():
        if param_key == "_unmapped":
            continue
        for e in entries:
            lines.append(f"{e['label']}: {_entry_text(e)}")
    return evidence.add(("specs", pid), product_id=pid, lang=row_lang, section_id=key, title=title or "Specifications",
                        page=page, pdf_page=pdf_page, text="\n".join(lines), kind="specs")


def _entry_text(e: dict) -> str:
    notes = [e[k] for k in ("variant", "condition") if e.get(k) and e[k] not in e["raw"]]
    return e["raw"] + (f" ({'; '.join(notes)})" if notes else "")


def get_specs(evidence: Evidence, conn, product_ids: list[str], parameters: list[str] | None = None,
              lang: str | None = None) -> str:
    product_ids = _check_products(product_ids)
    unknown = [p for p in parameters or [] if p not in store.PARAM_BY_KEY]
    if unknown:
        raise ValueError(f"Unknown parameters {unknown}. Valid: {', '.join(store.PARAM_BY_KEY)}")
    out = []
    for pid in product_ids:
        product = store.products()[pid]
        source = _spec_source(evidence, conn, pid, lang)
        if source is None:
            out.append(f"{product.name}: no specification table in the manual.")
            continue
        lines = [f"[{source.n}] {product.name} · {source.section_id} {source.title} · page {source.page}"]
        for key in parameters or [k for k in product.specs if k != "_unmapped"]:
            entries = product.specs.get(key)
            label = store.PARAM_BY_KEY[key]["labels"]["en"]
            if not entries:
                lines.append(f"  {label}: not stated in the manual")
                continue
            for e in entries:
                lines.append(f"  {label} (printed as \"{e['label']}\"): {_entry_text(e)}")
        if not parameters:
            for u in product.specs.get("_unmapped", []):
                lines.append(f"  {u['label']}: {u['raw'][:300]}")
        out.append("\n".join(lines))
    return "\n\n".join(out)


def _matches(entry: dict, op: str | None, value: float | None) -> bool | None:
    if op is None or value is None:
        return None
    if "min" not in entry:
        return None
    lo, hi = entry["min"], entry["max"]
    return {"<=": hi <= value, "<": hi < value, ">=": lo >= value, ">": lo > value,
            "=": lo <= value <= hi}[op]


def find_products(evidence: Evidence, conn, parameter: str, op: str | None = None, value: float | None = None,
                  family: str | None = None, kind: str | None = "robot", lang: str | None = None) -> str:
    param = store.PARAM_BY_KEY.get(parameter)
    if param is None:
        raise ValueError(f"Unknown parameter '{parameter}'. Valid: {', '.join(store.PARAM_BY_KEY)}")
    if op is not None and op not in ("<=", "<", ">=", ">", "="):
        raise ValueError("op must be one of <=, <, >=, >, =")

    rows, missing = [], []
    for product in store.products().values():
        if (kind and product.kind != kind) or (family and product.family != family):
            continue
        entries = [e for e in product.specs.get(parameter, []) if e.get("reviewed")]
        if not entries:
            missing.append(product.name)
            continue
        source = _spec_source(evidence, conn, product.id, lang)
        for e in entries:
            rows.append((product, e, _matches(e, op, value), source))

    reverse = param["better"] == "higher"
    rows.sort(key=lambda r: (r[1].get("max" if reverse else "min", 0) or 0), reverse=reverse)
    unit = param["unit"]
    head = f"Parameter: {param['labels']['en']}" + (f" (numbers compared in {unit})" if unit else "")
    if op and value is not None:
        head += f" · condition: {op} {value:g} {unit}".rstrip()
    scope = " · ".join(x for x in (f"kind: {kind}" if kind else "", f"family: {family}" if family else "") if x)
    lines = [head + (f" · {scope}" if scope else "")]
    for product, e, ok, source in rows:
        mark = "" if ok is None else ("  -> MATCH" if ok else "  -> no match")
        lines.append(f"[{source.n}] {product.name} ({product.family}): {_entry_text(e)}{mark}")
    if op and value is not None and not any(r[2] for r in rows):
        lines.append("No product matches the condition.")
    if missing:
        lines.append("Not stated in the manual for: " + ", ".join(missing))
    return "\n".join(lines)


# --- tool definitions for the model -----------------------------------------


def tool_schemas() -> list[dict]:
    ids = list(store.products())
    params = ", ".join(f"{p['key']} ({p['unit']})" if p["unit"] else p["key"] for p in store.SPEC_PARAMS)
    families = sorted({p.family for p in store.products().values()})
    lang = {"type": "string", "enum": list(store.LANGS),
            "description": "Language of the user's question if it is en, de or it; otherwise en."}
    return [
        {"type": "function", "function": {
            "name": "search_manuals",
            "description": ("Read the manuals. Use for how-to, troubleshooting, safety, indicators, parts and their "
                            "location, accessories and compatibility, and any detail of one or two products. "
                            "With one or two product_ids it returns their whole manuals plus the most relevant "
                            "sections of related accessories. Without product_ids it searches all manuals."),
            "parameters": {"type": "object", "required": ["query", "lang"], "properties": {
                "query": {"type": "string", "description": "What to look for, in the language of `lang`."},
                "product_ids": {"type": "array", "items": {"type": "string", "enum": ids}},
                "lang": lang}}}},
        {"type": "function", "function": {
            "name": "get_specs",
            "description": ("Specification values of given products, exactly as printed. Use for exact values and "
                            "for comparing products side by side."),
            "parameters": {"type": "object", "required": ["product_ids", "lang"], "properties": {
                "product_ids": {"type": "array", "items": {"type": "string", "enum": ids}},
                "parameters": {"type": "array", "items": {"type": "string", "enum": list(store.PARAM_BY_KEY)},
                               "description": "Leave out to get the whole specification table."},
                "lang": lang}}}},
        {"type": "function", "function": {
            "name": "find_products",
            "description": ("List products by one specification parameter, best first, optionally with a condition. "
                            "Use for 'which robot…' questions (narrowest, heaviest load, longest battery life, "
                            f"fits through X cm). Parameters and the unit numbers are compared in: {params}."),
            "parameters": {"type": "object", "required": ["parameter", "lang"], "properties": {
                "parameter": {"type": "string", "enum": list(store.PARAM_BY_KEY)},
                "op": {"type": "string", "enum": ["<=", "<", ">=", ">", "="]},
                "value": {"type": "number", "description": "In the parameter's unit."},
                "family": {"type": "string", "enum": families},
                "kind": {"type": "string", "enum": ["robot", "accessory"], "description": "Default: robot."},
                "lang": lang}}}},
    ]


TOOLS = {"search_manuals": search_manuals, "get_specs": get_specs, "find_products": find_products}
