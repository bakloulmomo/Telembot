# Ingestion: manuals → Postgres (pgvector)

Loads the PUDU manuals into the two tables described in [docs/7_rag_architecture.md](../docs/7_rag_architecture.md) and creates the embeddings.

## Setup (once)

```bash
python -m venv venv
venv/Scripts/python -m pip install -r ingest/requirements.txt     # macOS/Linux: venv/bin/python
```

Create `.env` in the repository root:

```
CONNECTION_STRING=postgresql://USER:PASSWORD@HOST:5432/postgres
OPENAI_API_KEY=sk-...
```

For Supabase, use the **Session pooler** connection string. The direct host (`db.<project>.supabase.co`) is IPv6-only and does not resolve on many networks.

The manuals are expected in `data/PUDU-PDF-MD/`. Set `DATA_DIR` in `.env` to use another folder.

## Run

```bash
# Pilot: two manuals
venv/Scripts/python ingest/load.py  --only bellabot-pro charging-station-light
venv/Scripts/python ingest/embed.py --only bellabot-pro charging-station-light

# Everything
venv/Scripts/python ingest/load.py
venv/Scripts/python ingest/embed.py

# Check
venv/Scripts/python ingest/verify.py
venv/Scripts/python ingest/search.py "indicator light is flashing yellow" --lang en
venv/Scripts/python ingest/search.py "where is the emergency stop" --product bellabot-pro
```

Both scripts can be run again at any time. `load.py` updates rows in place and clears the embedding of a section only if its text changed. `embed.py` sends only sections without an embedding.

## Files

| File | What it does |
|---|---|
| `schema.sql` | `vector` extension, tables `products` and `chunks`, indexes |
| `db.py` | Reads `.env`, opens the connection |
| `load.py` | Creates the tables, loads products and one row per manual section (text, page, figures with labels) |
| `embed.py` | Creates embeddings with OpenAI `text-embedding-3-small` (1536 dimensions) |
| `search.py` | Command-line vector search, for checking |
| `verify.py` | Compares the database with the manuals on disk (sections, text, pages, figures, embeddings) |
| `../shared/products.json` | Product registry (id, name, folder) |
| `../shared/product_extras.json` | Family, aliases and related products per product |
| `../backend/app/manuals.py` | Markdown parser, shared with the backend so section keys match |

`products.specs` is not filled yet: that is the next step.
