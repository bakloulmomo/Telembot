# Frontend Telembot

Vue 3 + Vite + TypeScript. Riproduce le schermate di `figma-design/`:

| Schermata | Componente |
|---|---|
| 01 · Ask | `App.vue` (pagina iniziale) + `Composer.vue` (`variant="home"`) |
| 01.5 · Searching | `ProgressSteps.vue`: eventi `progress` del backend (`search`, `read`, `check`) |
| 02 · Clarify | `ClarifyCard.vue`: `done.status = needs_clarification` e `done.options` |
| 03a · Answer · prose | `AnswerBody.vue`, testo con ① ② |
| 03b · Answer · numbered | `AnswerBody.vue`, quando la risposta è un elenco |
| 04a / 04b · Source panel | `SourcePanel.vue`: `/api/sources/…`, `citation.figures`, `citation.note` |

## Avvio

```bash
make dev                 # backend su :8000 (in un terminale)
make frontend-install    # la prima volta
make frontend            # frontend su http://localhost:5173
```

Vite inoltra `/api` e `/files` al backend (`BACKEND_URL`, predefinito `http://localhost:8000`).
Con il motore finto (`RAG_ENGINE=mock`) si vedono tutte le schermate:

- «How long does BellaBot charge, and what does it cost?» → chiarimento (BellaBot o BellaBot Pro),
  poi risposta con l'avviso sul prezzo;
- «Where is the lidar on the T300?» → risposta con la figura e la sua legenda.

## Dove cambiare cosa

- **Colori, font, misure**: `src/styles/base.css` (variabili `--…` in cima).
- **Testi dei passi**: `src/components/ProgressSteps.vue`.
- **Passaggio evidenziato nel manuale**: `src/lib/passage.ts` (confronta le frasi della risposta
  che citano la fonte con i blocchi della sezione).
- **Microfono**: `../backend/app/static/voice.js`, lo stesso file della pagina `/test` del backend.

## Comandi

```bash
npm run dev         # sviluppo
npm run typecheck   # controllo dei tipi
npm run build       # build di produzione in dist/
```
