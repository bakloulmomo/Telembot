"""Quick check of the vector search from the command line.

    python ingest/search.py "where is the emergency stop" --product bellabot-pro
    python ingest/search.py "gelbes Licht blinkt" --lang de
"""

from __future__ import annotations

import argparse
import sys

from openai import OpenAI

import db


def search(conn, client: OpenAI, query: str, product_ids: list[str] | None = None,
           lang: str | None = None, k: int = 5) -> list[tuple]:
    vector = client.embeddings.create(model=db.EMBEDDING_MODEL, input=[query]).data[0].embedding
    return conn.execute(
        """
        SELECT product_id, lang, section_key, section_title, section_kind, page,
               jsonb_array_length(figures) AS n_figures,
               1 - (embedding <=> %(v)s::vector) AS similarity
        FROM chunks
        WHERE embedding IS NOT NULL
          AND (%(products)s::text[] IS NULL OR product_id = ANY(%(products)s))
          AND (%(lang)s::text IS NULL OR lang = %(lang)s)
        ORDER BY embedding <=> %(v)s::vector
        LIMIT %(k)s
        """,
        {"v": vector, "products": product_ids, "lang": lang, "k": k},
    ).fetchall()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("--product", nargs="+", metavar="PRODUCT_ID")
    ap.add_argument("--lang", choices=["en", "de", "it"])
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    with db.connect() as conn:
        rows = search(conn, OpenAI(), args.query, args.product, args.lang, args.k)
    print(f'Query: "{args.query}"')
    for pid, lang, key, title, kind, page, n_figs, sim in rows:
        print(f"  {sim:.3f}  {pid:<24} {lang}  {key:<7} {(title or '')[:42]:<42} {kind:<15} p.{page}  figures={n_figs}")


if __name__ == "__main__":
    main()
