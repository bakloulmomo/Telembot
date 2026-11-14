# Frontend Telembot

È l'app del designer (Valerio), copiata così com'è dal branch `shares`, cartella
`valerio/telembot-frontend/app/`, e collegata al backend vero.
Regole, specifiche e schermate di riferimento sono lì: `README.md`, `DESIGN-SPEC.md`, `DATA.md`,
`animations/ANIMATIONS.md`, `screens/`.

```bash
cd frontend
npm ci          # le stesse versioni del designer (package-lock.json)
npm run dev     # http://localhost:5173, con il backend acceso su :8000
```

## Cosa è cambiato rispetto al codice del designer, e perché

| File | Cambiamento | Perché |
|---|---|---|
| `src/api/mock.js`, `src/components/PrototypeControls.vue`, `public/figures/` | **Tolti** | Niente dati finti: ogni domanda riceveva la risposta preparata su BellaBot. Le schermate con `?screen=…` e la barra "Play" restano nel branch `shares` per i confronti di design |
| `src/api/useChat.js` | Solo il flusso con il backend, sempre attivo (prima serviva `?live=1`) | Come sopra |
| `src/api/useChat.js` | Il chiarimento riprende lo stesso turno ("Your answer"), con la cronologia | Nel prototipo una scelta creava una domanda nuova, diversa dal design (02 → 03a) |
| `src/api/useChat.js` | Conteggi da `/api/products`, riga "Answer for … · from N pages …", avviso mostrato una volta sola | Dati veri al posto di quelli fissi; il RAG a volte ripete l'avviso nel testo |
| `src/api/useChat.js`, `src/api/chats.js` | Chat del cassetto salvate in questo browser | Il cassetto mostrava chat finte |
| `src/App.vue` | Senza barra del prototipo e senza `?screen`; conteggi e chat veri | Come sopra |
| `src/api/parse.js` | Toglie le etichette `[FIGURE …]`, trasforma gli elenchi in frasi; riga del manuale evidenziata anche con parole simili ("charges" / "Charging") e con un valore uguale ("4.5") | Problemi trovati con le risposte vere del RAG |
| `src/components/Composer.vue`, `PromptBar.vue`, `src/api/useVoice.js`, `vite.config.js` | Il microfono funziona (`backend/app/static/voice.js`) | Nel prototipo il pulsante non faceva nulla. Nessuno stile nuovo: cambia solo il testo del campo ("Listening…") |

Componenti, classi, token (`src/styles/tokens.css`), animazioni (`src/styles/motion.css`) e struttura
sono quelli del designer.
