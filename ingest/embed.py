"""Create embeddings for the sections that do not have one yet.

    python ingest/embed.py --only bellabot-pro     # pilot
    python ingest/embed.py                         # everything still missing

Safe to re-run: only rows with an empty embedding are sent to OpenAI.
"""

from __future__ import annotations

import argparse
import re

from openai import OpenAI

import db

BATCH = 64
MAX_CHARS = 24000          # about 6,000 tokens; the model accepts 8,191
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)\s*")


def embedding_text(product_name: str, number: str, title: str | None, content: str) -> str:
    """What is embedded: product and section name first, so that similar sections
    of different robots get different vectors. Image links are removed."""
    heading = f"{product_name} > {number} {title or ''}".strip()
    return f"{heading}\n\n{IMAGE_RE.sub('', content)}"[:MAX_CHARS]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", metavar="PRODUCT_ID", help="embed only these products (pilot run)")
    ap.add_argument("--limit", type=int, help="embed at most this many sections")
    args = ap.parse_args()

    client = OpenAI()  # reads OPENAI_API_KEY from the environment (.env)
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT c.id, p.name, c.section_key, c.section_title, c.content
            FROM chunks c JOIN products p ON p.id = c.product_id
            WHERE c.embedding IS NULL AND (%(only)s::text[] IS NULL OR c.product_id = ANY(%(only)s))
            ORDER BY c.product_id, c.lang, c.seq
            LIMIT %(limit)s
            """,
            {"only": args.only, "limit": args.limit},
        ).fetchall()
        if not rows:
            print("Nothing to embed.")
            return

        tokens = 0
        for start in range(0, len(rows), BATCH):
            batch = rows[start:start + BATCH]
            texts = [embedding_text(name, key, title, content) for _, name, key, title, content in batch]
            resp = client.embeddings.create(model=db.EMBEDDING_MODEL, input=texts)
            tokens += resp.usage.total_tokens
            for (chunk_id, *_), item in zip(batch, resp.data):
                if len(item.embedding) != db.EMBEDDING_DIM:
                    raise SystemExit(f"Model returned {len(item.embedding)} dimensions, schema expects {db.EMBEDDING_DIM}.")
                conn.execute("UPDATE chunks SET embedding = %s::vector WHERE id = %s", (item.embedding, chunk_id))
            conn.commit()  # keep progress if a later batch fails
            print(f"embedded {min(start + BATCH, len(rows))}/{len(rows)}")

    print(f"\nDone: {len(rows)} sections, {tokens} tokens, model {db.EMBEDDING_MODEL}.")


if __name__ == "__main__":
    main()
