"""Check that what is in the database matches the manuals on disk.

    python ingest/verify.py            # checks every product that is loaded
    python ingest/verify.py --quick    # skip the OpenAI round-trip check

Exit code 1 if any check fails.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys

from openai import OpenAI

import db
import embed
from app.manuals import HEADING_RE, NUMBERED_RE, PAGE_RE, SEPARATOR_RE, parse_manual

IMAGE_RE = re.compile(r"!\[[^\]]*\]\((images/[^)\s]+)\)")
LABEL_LIST_RE = re.compile(r"^\*(?:Labels|Beschriftungen|Etichette):?\*", re.M)

failures = 0


def check(name: str, passed: bool, info: object = "", show_pass: bool = True) -> None:
    global failures
    if not passed:
        failures += 1
        print(f"FAIL  {name}  {info}")
    elif show_pass:
        print(f"PASS  {name}  {info if info != '' else ''}".rstrip())


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="do not call OpenAI")
    args = ap.parse_args()

    conn = db.connect()
    q = lambda sql, *a: conn.execute(sql, a).fetchall()  # noqa: E731

    print("--- 1. Schema")
    check("vector extension installed", bool(q("SELECT 1 FROM pg_extension WHERE extname = 'vector'")))
    check("embedding column is vector(1536)",
          q("SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
            "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'")[0][0] == f"vector({db.EMBEDDING_DIM})")
    check("row level security on both tables",
          all(r[0] for r in q("SELECT relrowsecurity FROM pg_class WHERE relname IN ('products', 'chunks')")))

    print("--- 2. Products")
    registry = {p["id"]: p for p in json.loads(db.PRODUCTS_FILE.read_text(encoding="utf-8"))}
    extras = json.loads((db.PRODUCTS_FILE.parent / "product_extras.json").read_text(encoding="utf-8"))
    check("registry and extras list the same products", set(registry) == set(extras), f"{len(registry)} ids")
    check("related_products point to real ids",
          not [(k, r) for k, v in extras.items() for r in v["related_products"] if r not in registry])
    check("related_products are two-way",
          not [(k, r) for k, v in extras.items() for r in v["related_products"]
               if r in extras and k not in extras[r]["related_products"]])
    products = q("SELECT id, name, kind, langs, folder FROM products ORDER BY id")
    check("product rows match the registry",
          all(p[0] in registry and registry[p[0]]["name"] == p[1] and registry[p[0]]["category"] == p[2]
              and registry[p[0]]["folder"] == p[4] for p in products),
          f"{len(products)} of {len(registry)} products loaded")

    print("--- 3. Sections and figures against the files")
    n_sections = n_figures = n_label_lists = n_labelled = 0
    for pid, _name, _kind, langs, folder in products:
        on_disk = [l for l in ("en", "de", "it") if (db.DATA_DIR / folder / f"{l}.md").is_file()]
        check(f"{pid}: languages", sorted(langs) == sorted(on_disk), f"db={langs} disk={on_disk}", show_pass=False)
        for lang in langs:
            tag = f"{pid}/{lang}"
            path = db.DATA_DIR / folder / f"{lang}.md"
            text = path.read_text(encoding="utf-8")
            manual = parse_manual(path, lang)
            expected = [s for s in manual.sections if s.markdown]
            rows = q("SELECT section_key, page, pdf_page, content, figures FROM chunks "
                     "WHERE product_id = %s AND lang = %s ORDER BY seq", pid, lang)
            check(f"{tag}: same sections as the parser", [r[0] for r in rows] == [s.key for s in expected],
                  f"db={len(rows)} parser={len(expected)}", show_pass=False)
            check(f"{tag}: text and pages identical",
                  all(r[3] == s.markdown and r[1] == s.page and r[2] == s.pdf_page for r, s in zip(rows, expected)),
                  show_pass=False)
            body = text.split("\n---", 1)[1].splitlines()[1:] if text.startswith("---") else text.splitlines()
            stored = "\n".join(r[3] for r in rows)
            lost = [l for l in body if l.strip() and not PAGE_RE.match(l) and not SEPARATOR_RE.match(l)
                    and not ((h := HEADING_RE.match(l)) and NUMBERED_RE.match(h.group(2))) and l not in stored]
            check(f"{tag}: no manual line lost", not lost, lost[:2], show_pass=False)
            figures = [f for r in rows for f in r[4]]
            check(f"{tag}: every image is a figure, in order", [f["path"] for f in figures] == IMAGE_RE.findall(text),
                  f"db={len(figures)} file={len(IMAGE_RE.findall(text))}", show_pass=False)
            check(f"{tag}: image files exist, ids unique",
                  all((db.DATA_DIR / folder / f["path"]).is_file() for f in figures)
                  and len({f["id"] for f in figures}) == len(figures), show_pass=False)
            check(f"{tag}: PDF pages set and in order",
                  all(r[2] is not None for r in rows) and [r[2] for r in rows] == sorted(r[2] for r in rows),
                  show_pass=False)
            n_sections += len(rows)
            n_figures += len(figures)
            n_label_lists += len(LABEL_LIST_RE.findall(text))
            n_labelled += sum(1 for f in figures if f["labels"])
    if not failures:
        print(f"PASS  all files match  ({n_sections} sections, {n_figures} figures)")
    print(f"      label lists in the files: {n_label_lists} · figures with labels: {n_labelled}")

    print("--- 4. Embeddings")
    missing = q("SELECT count(*) FROM chunks WHERE embedding IS NULL")[0][0]
    check("every section has an embedding", missing == 0, f"{missing} missing")
    lo, hi = q("SELECT min(vector_norm(embedding)), max(vector_norm(embedding)) FROM chunks WHERE embedding IS NOT NULL")[0]
    check("vectors have unit length", lo is not None and 0.99 < lo and hi < 1.01, f"{lo:.4f}–{hi:.4f}" if lo else "")
    if not args.quick:
        client = OpenAI()
        ids = [r[0] for r in q("SELECT id FROM chunks WHERE embedding IS NOT NULL ORDER BY id")]
        random.seed(7)
        for chunk_id in random.sample(ids, min(5, len(ids))):
            pid, lang, key, name, title, content = q(
                "SELECT c.product_id, c.lang, c.section_key, p.name, c.section_title, c.content "
                "FROM chunks c JOIN products p ON p.id = c.product_id WHERE c.id = %s", chunk_id)[0]
            vector = client.embeddings.create(
                model=db.EMBEDDING_MODEL, input=[embed.embedding_text(name, key, title, content)]).data[0].embedding
            sim = q("SELECT 1 - (embedding <=> %s::vector) FROM chunks WHERE id = %s", vector, chunk_id)[0][0]
            # texts repeated word for word in several manuals share the top spot, so compare the score, not the id
            check(f"stored vector belongs to its text: {pid}/{lang}/{key}", sim > 0.999, f"similarity {sim:.4f}")

    print("--- 5. Summary")
    for row in q("SELECT lang, count(*), count(embedding) FROM chunks GROUP BY lang ORDER BY lang"):
        print(f"      {row[0]}: {row[1]} sections, {row[2]} embedded")
    print("      kinds:", ", ".join(f"{k} {n}" for k, n in
                                    q("SELECT section_kind, count(*) FROM chunks GROUP BY 1 ORDER BY 2 DESC")))

    print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
