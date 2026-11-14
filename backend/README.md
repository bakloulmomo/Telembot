# Telembot — backend

API FastAPI per l'assistente sui manuali PUDU: catalogo prodotti, testo delle fonti,
immagini e PDF, ricerca e chat in streaming. Usa il motore RAG del team (`rag/`) o qualsiasi altro
motore (vedi sotto). Non ha un motore finto: le risposte vengono sempre dal RAG vero.
I test automatici usano un motore finto solo per sé (`tests/stub_rag.py`), senza chiamare OpenAI.

## Avvio

Serve Python 3.11 o più recente. Dalla cartella principale del progetto:

```bash
make install   # una volta sola
make dev       # http://localhost:8000  ·  documentazione interattiva: http://localhost:8000/docs
make test      # 40 test
```

I manuali vanno in `data/` (accanto a `backend/`); per usarne un'altra imposta `DATA_DIR` in `backend/.env`.

## Endpoint

| Metodo | Percorso | Cosa fa |
|---|---|---|
| GET | `/api/health` | Stato, motore RAG attivo, numero di prodotti e sezioni |
| GET | `/api/products?category=&lang=` | I 22 prodotti con panoramica, immagine e specifiche chiave |
| GET | `/api/products/{id}?lang=` | Scheda: sezioni, tabelle specifiche, specifiche normalizzate, PDF |
| GET | `/api/compare?ids=a,b,c&lang=` | Specifiche affiancate di 2–4 prodotti |
| GET | `/api/sources/{id}/{lang}/{key}` | Testo di una sezione, con immagini e link al PDF alla pagina giusta |
| GET | `/files/{id}/{percorso}` | Immagini e PDF dei manuali (solo .png, .jpg, .pdf) |
| POST | `/api/search` | Solo retrieval |
| POST | `/api/chat` | Risposta in streaming SSE |
| POST | `/api/feedback` | Pollice su/giù su una risposta (salvato in `var/feedback.jsonl`) |
| POST | `/api/transcribe?lang=` | Domanda a voce: il corpo è l'audio (`audio/webm`, `audio/mp4`…), risponde `{"text"}` |
| GET | `/static/voice.js` | Microfono pronto da usare nel frontend (vedi sotto) |

`lang` accetta `it`, `en`, `de`. Se un manuale non esiste in quella lingua (FlashBot, GW1 e Pager
non hanno l'italiano) l'API restituisce l'inglese e lo indica nella risposta.

Esempi pronti da eseguire: `api.http` (VS Code con l'estensione REST Client, oppure IntelliJ/PyCharm).

### Streaming di `/api/chat`

```
event: sources   data: {"citations":[{"n":1,"product_id":"bellabot","section_id":"2.4","source_url":"/api/sources/bellabot/it/2.4", ...}]}
event: token     data: {"text":"La capacità della batteria è 25,6 Ah [1]"}
event: done      data: {"answer_id":"a_…","products":["bellabot"],"latency_ms":2140,"status":"answered","language":"it"}
event: error     data: {"code":"rag_timeout"|"rag_error","message":"…"}
```

Le fonti arrivano prima del testo. Dopo `error` non arriva `done`. Il backend non conserva la
conversazione: il frontend invia la cronologia in `history` a ogni domanda.

## Collegare un motore RAG

Il contratto è il minimo possibile: **domanda in ingresso, risposta e fonti in uscita**.

```python
def answer(question):                      # sincrona o async; history, lang, product_ids sono facoltativi
    return {"answer": "La batteria è da 25.6 Ah [1]",
            "sources": [{"text": "| Battery capacity | 25.6 Ah |", "source": "data/manuals/BellaBot_.../en.md"}]}
```

Il backend accetta anche una semplice stringa, una tupla `(testo, fonti)`, le chiavi usate da
LangChain e LlamaIndex (`result`, `response`, `output`, `source_documents`, `source_nodes`, `context`)
e gli oggetti `Document` / `NodeWithScore`. Una fonte può essere solo testo; i metadati
(`source`/`file`/`path`, `product_id`, `lang`, `section_id`, `page`, `score`) aiutano ma non servono:
`app/citations.py` ritrova prodotto, lingua e sezione dal percorso del file o dal testo del chunk,
e se il testo è ambiguo tra più robot lascia la fonte senza link invece di indovinare.

Le righe della tabella `chunks` prevista nell'architettura RAG (`docs/4_database_and_generalizability.md`)
vanno bene così come sono:

```json
{"product_slug": "bellabot_pro", "language": "en", "section_title": "2.4 Specifications",
 "page_label": "Page 3 (PDF page 4, left)", "block_type": "figure", "content": "…",
 "image_paths": ["manuals/BellaBot_Pro_User_Manual-multilanguage/images/en-p003R-fig01.png"]}
```

Lo slug può avere `_` o `-`. La sezione si ricava dal numero o dal titolo in `section_title`.
Immagini, in ordine di priorità: `figures` (le figure scelte dal motore, con la legenda:
`[{"path": "images/…", "caption", "labels": [{"n", "text"}]}]`), poi `image_paths`,
altrimenti tutte le immagini della sezione.

Due modi di collegarlo, scelti in `backend/.env`:

| `RAG_ENGINE` | Configurazione | Quando usarlo |
|---|---|---|
| `python` (predefinito) | `RAG_PYTHON=rag.pipeline:answer` (predefinito) | il RAG è codice Python nel repo (cartella `rag/`) |
| `http` | `RAG_URL=http://localhost:9000/ask` | il RAG è un servizio a parte, in qualsiasi linguaggio |

In modalità `http` il backend invia `POST {"question", "history", "lang", "product_ids"}` e accetta
in risposta gli stessi formati. La ricerca (`/api/search`) è facoltativa: `RAG_PYTHON_SEARCH` oppure
`RAG_SEARCH_URL`; senza, l'endpoint risponde 501.

## Domande a voce

`app/static/voice.js` registra la domanda e la trasforma in testo, senza dipendenze:

```js
import { createVoiceInput } from "http://localhost:8000/static/voice.js"   // o copiato nel frontend
const voice = await createVoiceInput({ apiBase: "http://localhost:8000", onText, onState, onError })
micButton.hidden = !voice.mode          // null = nessun modo disponibile
micButton.onclick = () => voice.toggle() // l'ascolto si ferma da solo dopo una pausa
```

- **Con `OPENAI_API_KEY`** (nel `.env` della radice o in `backend/.env`): l'audio va a `POST /api/transcribe`,
  che usa `TRANSCRIBE_MODEL` (predefinito `gpt-4o-mini-transcribe`). La lingua si riconosce da sola e i nomi
  dei prodotti sono nel prompt, così «BellaBot» e «CC1» vengono scritti giusti.
- **Senza chiave**: `/api/health` risponde `"transcription": false` e `voice.js` usa il riconoscimento vocale
  del browser (Chrome, Edge, Safari) nella lingua del browser. Su Firefox il microfono resta nascosto.

Il microfono funziona solo su `https` o su `localhost`. Si prova su `/test`.

## Sezioni dei manuali

`app/manuals.py` divide ogni manuale in sezioni ai titoli numerati (`## 2.4 …`). La chiave di una
sezione è il suo numero (`2.4`); il testo prima del primo titolo numerato è la sezione `0`; se un
numero si ripete nello stesso file la seconda sezione diventa `5.1~2`.

## Struttura

```
backend/
├── app/
│   ├── main.py          avvio, CORS, router
│   ├── settings.py      configurazione da .env
│   ├── schemas.py       modelli dell'API
│   ├── manuals.py       parser dei manuali (solo libreria standard)
│   ├── products.py      registro prodotti da shared/products.json
│   ├── catalog.py       catalogo in memoria, specifiche normalizzate, URL
│   ├── citations.py     da fonte del RAG a citazione con link
│   ├── presentation.py  chiarimento e tabella di confronto per l'interfaccia
│   ├── transcribe.py    da audio a testo (OpenAI), per le domande a voce
│   ├── static/          pagina di prova /test e voice.js
│   ├── rag/             contratto minimo, adattatori python/http
│   └── routes/          un file per gruppo di endpoint
├── tests/             test dell'API e del contratto con il RAG
└── api.http
```
