# RAG engine

Turns a question into an answer that uses only the manuals, with citations and figures.
Design: [docs/7_rag_architecture.md](../docs/7_rag_architecture.md). The database must be loaded first: see [ingest/README.md](../ingest/README.md).

## Use

```bash
venv/Scripts/python -m rag.ask "Where is the emergency stop on the BellaBot Pro?"
venv/Scripts/python -m rag.ask "Welcher Roboter passt durch einen 60 cm breiten Gang?" --debug
```

```python
from rag.pipeline import answer, search

result = answer("Which adapter is recommended for the T300?",
                history=[],            # earlier turns: [{"role": "user" | "assistant", "content": "..."}]
                lang=None,             # None = answer in the language of the question
                product_ids=None)      # products chosen in the interface, if any
```

`.env` in the repository root needs `CONNECTION_STRING` and `OPENAI_API_KEY`. Optional: `CHAT_MODEL` (default `gpt-4.1`), `EMBEDDING_MODEL` (default `text-embedding-3-small`, must match the one used for ingestion).

## What `answer()` returns

```json
{
  "answer": "The emergency stop switch on the BellaBot Pro is labeled as part number 20 … [1][2]",
  "status": "answered",
  "language": "en",
  "sources": [
    {"product_id": "bellabot-pro", "product_name": "BellaBot Pro", "lang": "en",
     "section_id": "2.3", "section_title": "Appearance & components", "page": 2, "pdf_page": 3,
     "text": "…", "score": null,
     "figures": [{"id": "bellabot-pro:en:p003R-fig01", "path": "images/en-p003R-fig01.png",
                  "caption": "2.3 Appearance & components", "labels": [{"n": "20", "text": "Emergency stop switch"}]}]}
  ],
  "debug": {"model": "gpt-4.1", "tool_calls": [], "unsupported_numbers": [], "dropped_figure_ids": [], "seconds": 3.1}
}
```

- A marker `[n]` in the answer is the n-th item of `sources` (starting at 1). Only cited sources are returned.
- `status`: `answered`, `not_in_docs` (the manuals do not cover it) or `needs_clarification` (the engine asks which product is meant).
- `figures` holds only the figures chosen for this answer. `path` is relative to the product's manual folder.
- This is the format the backend expects from `RAG_ENGINE=python` with `RAG_PYTHON=rag.pipeline:answer` and `RAG_PYTHON_SEARCH=rag.pipeline:search`.

## How it works

1. **Product names** in the question are found in code, from names and aliases in the database ("BellaBot Pro" is not also "BellaBot").
2. **The model must call a tool** before it answers, at most three rounds:
   - `search_manuals`: with one or two products it reads their whole manuals, plus the most relevant sections of related accessories; with none it searches all manuals by meaning and by exact words.
   - `get_specs`: specification values as printed, for one or more products.
   - `find_products`: products ranked or filtered by one parameter ("which robot…"). Uses reviewed values only.
3. **The model answers** in the user's language from the tool results only, and names the figures to show.
4. **Checks in code**: figure ids must be in the evidence; source numbers are renumbered to the cited ones; every number in the answer must appear in the evidence (one retry if not, then reported in `debug.unsupported_numbers`); an answer with no source becomes `not_in_docs`.

## Files

| File | Content |
|---|---|
| `pipeline.py` | `answer()` and `search()`, the prompt, the tool loop |
| `tools.py` | The three tools and the evidence they collect |
| `store.py` | Database queries, product name matching, settings |
| `checks.py` | Citation and number checks |
| `ask.py` | Command-line use |

## Tests

```bash
venv/Scripts/python eval/run_eval.py            # 25 questions with expected products, values, figures, status
venv/Scripts/python eval/run_eval.py fig-1 --show
```
