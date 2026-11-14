"""Fill products.specs from the specification tables of the English manuals.

    python ingest/load_specs.py              # parse, write to the database, print the comparison table
    python ingest/load_specs.py --dry-run    # parse and print only

How a table row becomes spec entries:
1. The label is matched to a standard parameter (shared/spec_parameters.json).
   Labels with no match are kept under "_unmapped", so nothing is lost.
2. The value is split into parts ("12 h (None load); 6 h (Max. load)" -> two entries).
3. Each part is parsed into numbers, converted to the parameter's unit.
4. shared/spec_overrides.json replaces the entries of rows that cannot be parsed
   automatically (broken tables, two values in one cell, values under a wrong label).

Every entry keeps `raw`, the text exactly as printed. An entry gets `reviewed: true`
when it was parsed completely or written by hand, and `raw` is found word for word
in the manual. Only reviewed entries should be used for filters and rankings.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from psycopg.types.json import Jsonb

import db
from app.manuals import Manual, Section, parse_manual, parse_tables

SHARED = db.PRODUCTS_FILE.parent
CONFIG = json.loads((SHARED / "spec_parameters.json").read_text(encoding="utf-8"))
PARAMS = CONFIG["parameters"]
UNITS = {k: v for k, v in CONFIG["units"].items() if not k.startswith("_")}
PARAM_BY_KEY = {p["key"]: p for p in PARAMS}
_PARAM_RES = [(p, re.compile(rf"^\s*(?:{p['match']})", re.I)) for p in PARAMS]

SPEC_TITLE_RE = re.compile(r"specification|parameter", re.I)
GENERIC_HEADER_RE = re.compile(r"(description|values?|parameters?|specifications?|details?)?", re.I)

# --- finding the table -------------------------------------------------------


def spec_section(manual: Manual) -> Section | None:
    candidates = [s for s in manual.sections if s.number and SPEC_TITLE_RE.search(s.title) and "|" in s.markdown]
    chapter2 = [s for s in candidates if s.number.startswith("2")]
    return (chapter2 or candidates or [None])[0]


def table_rows(section: Section) -> list[tuple[str, list[tuple[str | None, str]]]]:
    """[(label, [(column name or None, cell text)])] for every data row of the section.

    Tables with several value columns (one per adapter, for example) give one cell per
    column, named after the first value of that column when the header is generic.
    """
    out = []
    for header, rows in parse_tables(section.markdown):
        if len(header) >= 2 and not GENERIC_HEADER_RE.fullmatch(header[-1].strip()):
            rows = [header, *rows]          # the "header" is really a data row
        for cells in rows:
            if len(cells) < 2 or not cells[0].strip():
                continue
            label, values = cells[0].strip(), [c.strip() for c in cells[1:]]
            if label.lower() in ("feature", "features", "item", "product feature", "specifications",
                                 "product characteristics") and all(GENERIC_HEADER_RE.fullmatch(v) for v in values):
                continue                    # a header row repeated inside the table
            values = [v for v in values if v and v != label]
            if not values:
                continue
            if len(set(values)) == 1:
                out.append((label, [(None, values[0])]))
            elif len(values) == 2 and values[1].startswith(values[0]) is False and len(cells) == 3:
                # "Max. transmit power | Wi-Fi | 17.48 dBm": sub-label + value
                out.append((label, [(values[0], values[1])]))
            else:
                out.append((label, [(f"column {i + 1}", v) for i, v in enumerate(values)]))
    return out


# --- parsing a value ---------------------------------------------------------

DASH = r"(?:-|–|—|~|～|to)"
NUM = r"\d+(?:\.\d+)?"
OP_WORDS = {"<": "<", ">": ">", "≥": ">=", ">=": ">=", "≤": "<=", "<=": "<=",
            "about": "~", "approximately": "~", "approx.": "~", "approx": "~", "max.:": "<=", "max.": "<="}
WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
MODEL_CODE_RE = re.compile(r"^[A-Z]{2,}[A-Z0-9]*\d[A-Z0-9]*$")
IP_RE = re.compile(r"^IP[X\d]{2}$")
DIM_SEP = r"\s*(?:x|×|\*)\s*"


def clean(text: str) -> str:
    text = text.replace("&nbsp;", " ").replace("：", ":").replace("；", ";").replace("，", ",")
    text = text.replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", " ", text).strip()


def split_parts(cell: str) -> list[str]:
    """'12 h (None load); 6 h (Max. load)' -> two parts. Parts keep their exact text."""
    parts = [p.strip() for p in re.split(r"<br>|;|；", cell.replace("&nbsp;", " ")) if p.strip()]
    return parts or [cell]


def _unit_factor(param: dict, unit: str) -> float | None:
    table = UNITS.get(param["unit"], {})
    return table.get(unit.lower().replace(" ", ""))


def parse_part(param: dict, part: str) -> dict:
    """One printed value -> entry fields. `parsed` is True only if the whole text was understood."""
    entry: dict = {"raw": part}
    text = clean(part)

    # "SWFD01: 49 kg", "Normal Mode: 70 mins", "Flat surface: 15 kg/layer"
    if m := re.match(r"^([A-Za-z][^:]{0,45}):\s*(.+)$", text):
        entry["variant"], text = m.group(1).strip(), m.group(2).strip()
    # trailing "(unloaded)", "(WTID01)", "(from 0% to 90%)"
    if m := re.match(r"^(.*?)\s*\(([^()]*)\)$", text):
        note, text = m.group(2).strip(), m.group(1).strip()
        if MODEL_CODE_RE.match(note):
            entry["variant"] = note
        else:
            entry["condition"] = note

    if param["type"] == "text":
        entry["parsed"] = bool(text) and (param["key"] != "ip_rating" or bool(IP_RE.match(text)))
        return entry

    if param["type"] == "dimensions":
        m = re.match(rf"^({NUM})\s*(mm|cm|m)?{DIM_SEP}({NUM})\s*(mm|cm|m)?{DIM_SEP}({NUM})\s*(mm|cm|m)?$", text, re.I)
        unit = (m.group(6) or m.group(4) or m.group(2)) if m else None
        factor = _unit_factor(param, unit) if unit else None
        if m and factor:
            entry["values"] = [round(float(m.group(i)) * factor, 2) for i in (1, 3, 5)]
            entry["unit"] = param["unit"]
        entry["parsed"] = "values" in entry
        return entry

    # number or range: "< 3 h", "0.2-1.2 m/s", "10 h ~ 24 h", "About 3h", "10 kg/layer", "70cm"
    unit_rx = r"[A-Za-z°º㎡²][A-Za-z°º㎡²/ ]*?"
    op_rx = r"(?P<op><=|>=|[<>≥≤]|about|approximately|approx\.?|max\.:?)?\s*"
    per_rx = r"(?P<per>\s*/\s*(?:layer|level|tray))?$"
    m = (re.match(rf"^{op_rx}(?P<a>{NUM})\s*(?:{unit_rx})?\s*{DASH}\s*(?P<b>{NUM})\s*(?P<u>{unit_rx})?{per_rx}", text, re.I)
         or re.match(rf"^{op_rx}(?P<a>{NUM})\s*(?P<u>{unit_rx})?{per_rx}", text, re.I))
    if not m and not param["unit"]:        # counts: "Four", "Four (adjustable)", "3"
        word = text.lower()
        if word in WORD_NUMBERS or re.fullmatch(r"\d+", word):
            n = WORD_NUMBERS.get(word) or int(word)
            entry.update(op="=", min=n, max=n, unit="", parsed=True)
            return entry
    if m:
        unit = (m.group("u") or "").strip()
        if not param["unit"] and not unit:
            factor = 1
        else:
            factor = _unit_factor(param, re.sub(r"\s+", "", unit))
        if factor:
            a = float(m.group("a")) * factor
            b = float(m.group("b")) * factor if m.groupdict().get("b") else a
            op = OP_WORDS.get((m.group("op") or "").lower(), "=")
            entry.update(op=op, min=round(min(a, b), 3), max=round(max(a, b), 3), unit=param["unit"])
            if m.group("per"):
                entry.setdefault("condition", "per tray")
            entry["parsed"] = True
            return entry
    entry["parsed"] = False
    return entry


# --- building the specs of one product ---------------------------------------


def find_param(label: str) -> dict | None:
    label = clean(label)
    for param, rx in _PARAM_RES:
        if rx.match(label):
            return param
    return None


def build_specs(product_id: str, manual: Manual, overrides: dict) -> tuple[dict, list[str]]:
    section = spec_section(manual)
    notes: list[str] = []
    if section is None:
        return {}, ["no specification section found"]
    source_text = section.markdown
    where = {"section": section.key, "page": section.page, "pdf_page": section.pdf_page}
    relabel = overrides.get("relabel", {})          # printed label -> parameter key
    replaced = overrides.get("entries", {})         # parameter key -> hand-written entries
    drop_labels = set(overrides.get("skip_labels", []))

    specs: dict[str, list[dict]] = {}
    unmapped: list[dict] = []
    for label, cells in table_rows(section):
        if label in drop_labels:
            continue
        key = relabel.get(label)
        param = PARAM_BY_KEY[key] if key else find_param(label)
        for column, cell in cells:
            if param is None:
                item = {"label": label, "raw": cell, **where}
                if column:
                    item["variant"] = column
                unmapped.append(item)
                continue
            if param["key"] in replaced:
                continue                            # written by hand below
            for part in split_parts(cell):
                entry = parse_part(param, part)
                parsed = entry.pop("parsed")
                if column and "variant" not in entry:
                    entry["variant"] = column
                entry.update(label=label, **where, source="auto",
                             reviewed=bool(parsed and entry["raw"] in source_text))
                specs.setdefault(param["key"], []).append(entry)

    for key, entries in replaced.items():
        param = PARAM_BY_KEY[key]
        specs[key] = []
        for e in entries:
            entry = dict(e)
            if "min" in entry or "values" in entry:
                entry.setdefault("unit", param["unit"])
                if "min" in entry:
                    entry.setdefault("op", "=")
                    entry.setdefault("max", entry["min"])
            found = entry["raw"] in source_text
            if not found:
                notes.append(f"override for {key}: raw text {entry['raw']!r} is not in the manual")
            entry.update(**where, source="manual", reviewed=found)
            specs[key].append(entry)

    # keep the parameter order of the config file
    ordered = {p["key"]: specs[p["key"]] for p in PARAMS if p["key"] in specs}
    if unmapped:
        ordered["_unmapped"] = unmapped
    return ordered, notes


# --- report ------------------------------------------------------------------

REPORT_KEYS = ["min_passage_width", "max_load", "load_per_tray", "tray_count", "battery_runtime", "charging_time",
               "battery_capacity", "weight", "dimensions", "speed", "max_obstacle_height", "max_climbing_angle",
               "ip_rating"]


def show(entry: dict) -> str:
    if "values" in entry:
        body = "×".join(f"{v:g}" for v in entry["values"])
    elif "min" in entry:
        body = f"{entry['min']:g}" if entry["min"] == entry["max"] else f"{entry['min']:g}-{entry['max']:g}"
        body = ("" if entry.get("op", "=") == "=" else entry["op"]) + body
    else:
        body = entry["raw"][:22]
    tag = entry.get("variant") or entry.get("condition")
    return f"{body}{'[' + tag[:14] + ']' if tag else ''}{'' if entry['reviewed'] else ' ??'}"


def report(all_specs: dict[str, dict], kinds: dict[str, str]) -> None:
    for kind in ("robot", "accessory"):
        print(f"\n=== {kind.upper()}  (numbers in the parameter's unit; '??' = not reviewed, not used for filters)")
        for key in REPORT_KEYS:
            rows = [(pid, s[key]) for pid, s in all_specs.items() if kinds[pid] == kind and key in s]
            if not rows:
                continue
            print(f"\n{key} [{PARAM_BY_KEY[key]['unit'] or '-'}]")
            for pid, entries in rows:
                print(f"  {pid:<24} {' | '.join(show(e) for e in entries)}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="parse and print, do not write to the database")
    ap.add_argument("--quiet", action="store_true", help="do not print the comparison table")
    args = ap.parse_args()

    registry = json.loads(db.PRODUCTS_FILE.read_text(encoding="utf-8"))
    overrides = json.loads((SHARED / "spec_overrides.json").read_text(encoding="utf-8"))
    all_specs: dict[str, dict] = {}
    problems: list[str] = []
    for p in registry:
        manual = parse_manual(db.DATA_DIR / p["folder"] / "en.md", "en")
        specs, notes = build_specs(p["id"], manual, overrides.get(p["id"], {}))
        all_specs[p["id"]] = specs
        problems += [f"{p['id']}: {n}" for n in notes]

    if not args.quiet:
        report(all_specs, {p["id"]: p["category"] for p in registry})

    print("\n=== summary")
    for pid, specs in all_specs.items():
        entries = [e for k, v in specs.items() if k != "_unmapped" for e in v]
        print(f"  {pid:<24} parameters={len(specs) - ('_unmapped' in specs):<3} entries={len(entries):<3} "
              f"reviewed={sum(e['reviewed'] for e in entries):<3} unmapped rows={len(specs.get('_unmapped', []))}")
    for line in problems:
        print("  PROBLEM", line)

    if args.dry_run:
        print("\nDry run: nothing written.")
        return
    with db.connect(vectors=False) as conn:
        for pid, specs in all_specs.items():
            conn.execute("UPDATE products SET specs = %s WHERE id = %s", (Jsonb(specs), pid))
        conn.commit()
    print(f"\nWrote specs for {len(all_specs)} products.")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
