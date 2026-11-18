# Telembot

**Answers from the PUDU manuals, with the page they come from.**
NOI Hackathon / SFSCON 2026 · Telmekom challenge · team 13

Telembot turns 22 PUDU robot and accessory manuals (English, German, Italian) into a conversational assistant for two kinds of users: technicians (exact values, procedures, troubleshooting) and non-technical users such as sales staff (which robot fits a need, how products compare).

- **Grounded:** every statement carries the number of its source; one click opens the manual page with the cited line highlighted, the figure and the original PDF at the right page.
- **Honest:** what the manuals do not cover (for example prices) is shown as "Not in the manuals", never invented. Every number in an answer is checked in code against the cited sources.
- **Multilingual:** answers in the language of the question, whatever the language of the manual.
- **API-first:** search, sources, product catalog and comparison are REST endpoints; the RAG engine sits behind a minimal contract and can be swapped.
- **Results:** 25 of 25 test questions pass, about 3 seconds per answer.

**Stack:** Vue 3 + Vite (design by the team's designer) · FastAPI (streaming answers) · PostgreSQL + pgvector · OpenAI `gpt-4.1` with tools and `text-embedding-3-small`.

**Team:** Mohamed (backend and frontend) · Azam Afridi (RAG, architecture docs, number audit) · rosponiv-star (database, ingestion, RAG engine) · Valerio (UX/UI and Figma design).

The PUDU manuals are not in this repository (copyright Shenzhen Pudu Technology Co., Ltd.): put them in `data/` as described below.

## What is in the repository

| Folder | Content |
|---|---|
| `frontend/` | The web app (Vue 3): chat, live progress, sources panel, comparison table, chats, voice. See [frontend/README.md](frontend/README.md) |
| `ingest/` | Loads the manuals into Postgres (pgvector): sections, figures, embeddings, specs. See [ingest/README.md](ingest/README.md) |
| `rag/` | The RAG engine: question → grounded answer. See [rag/README.md](rag/README.md) |
| `backend/` | FastAPI: chat (streaming), search, product catalog, sources, images and PDFs, voice. See [backend/README.md](backend/README.md) |
| `eval/` | 25 test questions and a runner |
| `shared/` | Product registry, spec parameters and overrides |
| `docs/` | Design, plan and progress notes. Start with [docs/7_rag_architecture.md](docs/7_rag_architecture.md) |

## What works today

- All 22 manuals (EN / DE / IT) are in the database: 922 sections, 476 figures, 223 spec values.
- The engine answers how-to, troubleshooting, spec, comparison, "which robot…" and accessory questions, in the user's language, with citations.
- Figures are returned with their label list when the question is about a part or a procedure step.
- Questions the manuals do not cover get a clear "not in the documentation" answer.
- The web app (`frontend/`) shows all of this: live progress, answers with sources, the manual page with the cited line, figures, "Not in the manuals", comparison tables, saved chats and voice input.

---

## Commands

All commands are run from the repository root (`team-13/`).
On macOS / Linux, write `venv/bin/python` instead of `venv/Scripts/python`.

### 1. Set up (once)

Needs Python 3.11 or newer.

```bash
python -m venv venv
```

```bash
venv/Scripts/python -m pip install -r ingest/requirements.txt fastapi uvicorn pydantic-settings httpx pytest
```

Put the dataset in `data/PUDU-PDF-MD/` (the folder that contains `manuals/` and `accessories/`). It is not in the repository.

Create `.env` in the repository root:

```
CONNECTION_STRING=postgresql://USER:PASSWORD@HOST:5432/postgres
OPENAI_API_KEY=sk-...
```

For Supabase, use the **Session pooler** connection string, not the direct one.

Create `backend/.env`:

```
DATA_DIR=../data/PUDU-PDF-MD
RAG_ENGINE=python
RAG_PYTHON=rag.pipeline:answer
RAG_PYTHON_SEARCH=rag.pipeline:search
```

Both `.env` files are ignored by Git. Never commit them.

### 2. Load the database (once, or after the manuals change)

Skip this if the team database is already loaded: everyone with the same `CONNECTION_STRING` shares it.

```bash
venv/Scripts/python ingest/load.py
```

```bash
venv/Scripts/python ingest/embed.py
```

```bash
venv/Scripts/python ingest/load_specs.py
```

Check that the database matches the manuals:

```bash
venv/Scripts/python ingest/verify.py
```

All three loading commands can be run again safely. Only sections whose text changed are embedded again.

### 3. Start the system

```bash
venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000
```

Wait for the line `Application startup complete`. Then start the web app in a second terminal (Node.js 18 or newer):

```bash
cd frontend
npm ci
npm run dev
```

and open:

| Address | What |
|---|---|
| http://localhost:5173 | **The web app** |
| http://localhost:8000/test | Developer test chat: answer, sources and figures |
| http://localhost:8000/docs | All API endpoints, with a "Try it out" button |
| http://localhost:8000/api/health | Quick check: engine in use, number of products |

While developing, add `--reload` to restart the server automatically when a file changes:

```bash
venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000 --reload
```

### 4. Stop the system

Press **Ctrl + C** in the terminal where the server is running.

If the terminal is gone and port 8000 is still in use:

Windows (PowerShell), find the process and stop it:

```bash
netstat -ano | findstr :8000
```

```bash
taskkill /PID <number from the last column> /F
```

macOS / Linux:

```bash
lsof -ti:8000 | xargs kill
```

Or start on another port by changing `--port 8000` to `--port 8001`.

The database is hosted (Supabase), so there is nothing to stop on that side.

### 5. Ask a question without the server

```bash
venv/Scripts/python -m rag.ask "Where is the emergency stop on the BellaBot Pro?"
```

Add `--debug` to see which tools were called and the result of the checks:

```bash
venv/Scripts/python -m rag.ask "Welcher Roboter passt durch einen 60 cm breiten Gang?" --debug
```

Search only, no answer:

```bash
venv/Scripts/python ingest/search.py "indicator light is flashing yellow" --lang en
```

### 6. Run the tests

The 25 test questions (takes about half a minute, uses the OpenAI API):

```bash
venv/Scripts/python eval/run_eval.py
```

One question, with the full answer printed:

```bash
venv/Scripts/python eval/run_eval.py fig-1 --show
```

The backend's own tests (no API calls: they use a test-only fake engine, `backend/tests/stub_rag.py`):

```bash
cd backend && ../venv/bin/python -m pytest -q
```

---

## If something does not work

| Symptom | Likely cause |
|---|---|
| `failed to resolve host 'db.….supabase.co'` | The direct Supabase host is IPv6-only. Use the Session pooler connection string |
| `Cartelle mancanti in …` at server start | `DATA_DIR` in `backend/.env` does not point to the folder that contains `manuals/` and `accessories/` |
| `Set CONNECTION_STRING in .env` | The root `.env` is missing or in the wrong folder |
| The test page answers "Non è stato possibile generare la risposta" | The engine failed: look at the server terminal for the error (usually the OpenAI key or the database connection) |
| Port 8000 already in use | See "Stop the system", or use another port |
