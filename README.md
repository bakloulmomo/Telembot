# team-13 · Telembot

Conversational access to the PUDU robot manuals: ask a question in any language and get an answer taken only from the manuals, with citations and the relevant figure.

| Folder | Content |
|---|---|
| `ingest/` | Loads the manuals into Postgres (pgvector): sections, figures, embeddings, specs. See [ingest/README.md](ingest/README.md) |
| `rag/` | The RAG engine: question → grounded answer. See [rag/README.md](rag/README.md) |
| `backend/` | FastAPI: chat (streaming), search, product catalog, images and PDFs. See [backend/README.md](backend/README.md) |
| `eval/` | 25 test questions and a runner |
| `shared/` | Product registry, spec parameters and overrides |
| `docs/` | Design, plan and progress notes. Start with [docs/7_rag_architecture.md](docs/7_rag_architecture.md) |

## Run it locally

Needs Python 3.11 or newer, the dataset in `data/PUDU-PDF-MD/`, and a Postgres database with the `vector` extension that has been loaded with `ingest/` (see its README).

**1. Install (once)**

```bash
python -m venv venv
venv/Scripts/python -m pip install -r ingest/requirements.txt fastapi uvicorn pydantic-settings httpx
```

On macOS / Linux use `venv/bin/python` instead of `venv/Scripts/python`.

**2. Settings (once)**

`.env` in the repository root:

```
CONNECTION_STRING=postgresql://USER:PASSWORD@HOST:5432/postgres
OPENAI_API_KEY=sk-...
```

`backend/.env`:

```
DATA_DIR=../data/PUDU-PDF-MD
RAG_ENGINE=python
RAG_PYTHON=rag.pipeline:answer
RAG_PYTHON_SEARCH=rag.pipeline:search
```

**3. Start the server**

```bash
venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000
```

**4. Try it**

| Address | What |
|---|---|
| http://localhost:8000/test | Test chat: ask a question, see the answer, sources and figures |
| http://localhost:8000/docs | All API endpoints |

Without the server, from the terminal:

```bash
venv/Scripts/python -m rag.ask "Where is the emergency stop on the BellaBot Pro?" --debug
venv/Scripts/python eval/run_eval.py
```
