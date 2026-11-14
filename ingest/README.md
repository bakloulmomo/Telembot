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
venv/Scripts/python ingest/load_specs.py      # fills products.specs, prints the comparison table

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
| `load_specs.py` | Reads the specification tables of the English manuals into `products.specs` (use `--dry-run` to only print) |
| `search.py` | Command-line vector search, for checking |
| `verify.py` | Compares the database with the manuals on disk (sections, text, pages, figures, embeddings) |
| `../shared/products.json` | Product registry (id, name, folder) |
| `../shared/product_extras.json` | Family, aliases and related products per product |
| `../shared/spec_parameters.json` | Standard spec parameters: label patterns, unit, display labels in EN/DE/IT |
| `../shared/spec_overrides.json` | Hand-written fixes for rows the parser cannot read (broken table, two values in one cell, wrong label) |
| `../backend/app/manuals.py` | Markdown parser, shared with the backend so section keys match |

## Specs

Each parameter in `products.specs` holds a list of entries. `raw` is the value as printed; `min`, `max` (or `values` for dimensions) are numbers in the parameter's unit; `variant` and `condition` say what the value applies to. Rows whose label is not a standard parameter are kept under `_unmapped`.

`reviewed: true` means the value was parsed completely, or written by hand in `spec_overrides.json`, and its `raw` text is found word for word in the manual. Use only reviewed entries for filters and rankings.
