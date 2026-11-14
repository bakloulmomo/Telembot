# Frontend Telembot

Vue 3 + Vite. È il prototipo del designer (Valerio, branch `shares`, cartella
`valerio/telembot-frontend/`), con gli stessi componenti, token e regole, collegato al backend vero.

**Le regole del designer valgono anche qui:** valori solo da `src/styles/tokens.css`, font Geist,
icone Material Symbols, nessuna animazione a parte lo spinner (arriveranno in `animations/`).
Specifiche: `DESIGN-SPEC.md` e `DATA.md` nel branch `shares`.

## Avvio

```bash
make dev                 # backend su :8000
make frontend-install    # la prima volta
make frontend            # http://localhost:5173
```

| Indirizzo | Cosa mostra |
|---|---|
| `http://localhost:5173/` | L'app collegata al backend (`/api/chat`, `/api/sources`, `/api/compare`, `/api/products`) |
| `?mock=1` | I dati finti del designer |
| `?screen=04a&clean=1` | Una schermata del Figma (`00`, `01`, `01.5`, `02`, `03a`, `03c`, `04a`, `04b`) per confrontarla con i PNG |

## Cosa è stato aggiunto al prototipo

| File | Cosa |
|---|---|
| `src/api/useChat.js` | Flusso vero: avanzamento, chiarimento che riprende lo stesso turno («Your answer»), stop, domande di seguito con la cronologia, risposta «plain» con tabella da `/api/compare`, chat salvate. Il flusso finto del designer è intatto |
| `src/api/backend.js` | Conteggi, sezione del manuale dal backend trasformata nelle righe del «document snapshot» (senza le descrizioni AI delle figure), confronto |
| `src/api/chats.js` | Chat del cassetto a sinistra, salvate in questo browser |
| `src/api/useVoice.js` | Microfono: `backend/app/static/voice.js` |
| `src/api/parse.js` | Testo del motore («hours [1].», elenchi, grassetto) nel formato del design; riga evidenziata scelta per parole in comune |

## Campi facoltativi che il motore RAG può aggiungere

Il frontend li usa già se arrivano nell'evento `done` o nelle fonti (`DATA.md`); senza, usa i ripieghi descritti lì.

- `style`: `technical` / `plain`
- `short_answer.values[]`: i valori grandi in alto (`4.5 h`)
- `gaps[].topic`: «Price: not in the manuals»
- `clarification.reason`
- `comparison`, `cited_lines` / `line`
