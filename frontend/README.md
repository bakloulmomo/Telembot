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

| `src/App.vue`, `SourcePanel.vue`, `ChatsDrawer.vue`, `HomeView.vue`, `TopBar.vue`, `Turn.vue`, `ComparisonTable.vue` | Funziona su ogni dimensione di finestra: altezza `100dvh`, niente `min-width: 1100px`. Sotto 1100 px pannello e cassetto si sovrappongono alla pagina (non c'è spazio per spingerla); sotto 760 px le due schede iniziali vanno in colonna e la tabella scorre di lato; sotto 640 px margini di 16 px e conteggi nascosti; con finestre basse la pagina iniziale scorre | Lo spec descrive solo 1440 × 1024. Con `min-width: 1100px` sotto quella larghezza la pagina scorreva di lato e il pannello e il pulsante "Open manual" uscivano dallo schermo (anche a 1366 px con zoom 125%). Sopra 1100 px resta identico allo spec: barra a 40 px dal fondo, pannello alto quanto la finestra con intestazione e pulsante fissi |
| `src/components/TopBar.vue` | Con il cassetto aperto i conteggi vanno a sinistra | Come nel PNG 00 (nel prototipo restavano a destra) |
| `src/components/Turn.vue` | Il blocco della risposta breve compare solo se ha qualcosa da mostrare | Senza `short_answer` dal RAG il blocco vuoto aggiungeva un secondo spazio di 36 px sopra DETAILS |
| `src/api/useChat.js` | Un avviso uguale compare una volta; "Found: No source in the manuals" nel pannello 04c; nelle risposte plain la prima frase breve diventa il titolo | Ripieghi di `DATA.md` e `DESIGN-SPEC.md` 1.11b quando il RAG non manda `gaps[].found` e `short_answer` |

Componenti, classi, token (`src/styles/tokens.css`), animazioni (`src/styles/motion.css`) e struttura
sono quelli del designer.
