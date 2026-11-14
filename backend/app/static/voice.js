// Domande a voce per Telembot. Nessuna dipendenza: si usa nella pagina /test e nel frontend Vue.
//
// Sceglie da solo il modo:
//  - "server":  registra dal microfono e invia l'audio a POST /api/transcribe (OpenAI).
//               Riconosce la lingua da sola. Usato se GET /api/health risponde transcription: true.
//  - "browser": riconoscimento vocale del browser (Web Speech API: Chrome, Edge, Safari),
//               nella lingua del browser. Usato se il server non ha OPENAI_API_KEY.
//  - null:      nessuno dei due è disponibile (es. Firefox senza chiave): nascondere il microfono.
//
//   const voice = await createVoiceInput({ onText, onState, onError })
//   voice.mode            "server" | "browser" | null
//   voice.toggle()        avvia l'ascolto, o lo ferma se è già attivo
//   voice.cancel()        ferma senza trascrivere
//   onState(state)        "idle" | "listening" | "transcribing"
//   onText(text)          la domanda riconosciuta
//   onError(message)      messaggio breve da mostrare
//
// L'ascolto si ferma da solo dopo una pausa di silenzio. Il microfono funziona solo su
// https o su localhost.

const SILENCE_MS = 1500;     // pausa che chiude la frase
const NO_SPEECH_MS = 8000;   // nessuna voce: si annulla
const MAX_MS = 30000;        // durata massima
const THRESHOLD = 0.02;      // volume minimo considerato voce
const LOCALES = { en: "en-US", de: "de-DE", it: "it-IT" };

export async function createVoiceInput({ apiBase = "", lang = null, onText, onState = () => {}, onError = () => {} } = {}) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const canRecord = !!(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
  let serverOk = false;
  try {
    const r = await fetch(`${apiBase}/api/health`);
    serverOk = r.ok && (await r.json()).transcription === true;
  } catch { /* backend non raggiungibile: si prova il browser */ }

  const mode = serverOk && canRecord ? "server" : Recognition ? "browser" : null;
  let state = "idle";
  let stop = null;
  const setState = s => { state = s; onState(s); };

  function micError(err) {
    if (err?.name === "NotAllowedError" || err === "not-allowed") return "Microphone permission denied.";
    if (err?.name === "NotFoundError") return "No microphone found.";
    return "Microphone not available.";
  }

  async function startServer() {
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      onError(micError(err));
      return;
    }
    const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]
      .find(t => MediaRecorder.isTypeSupported?.(t));
    const recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
    const chunks = [];
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };

    // volume dal microfono, per chiudere la frase quando si smette di parlare
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const buf = new Float32Array(analyser.fftSize);
    const t0 = performance.now();
    let spoke = false, lastVoice = t0, reason = "manual";
    const timer = setInterval(() => {
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += v * v;
      const now = performance.now();
      if (Math.sqrt(sum / buf.length) > THRESHOLD) { spoke = true; lastVoice = now; }
      if (spoke && now - lastVoice > SILENCE_MS) stop?.("silence");
      else if (!spoke && now - t0 > NO_SPEECH_MS) stop?.("nospeech");
      else if (now - t0 > MAX_MS) stop?.("max");
    }, 100);

    stop = why => {
      reason = why;
      stop = null;
      if (recorder.state !== "inactive") recorder.stop();
    };

    recorder.onstop = async () => {
      clearInterval(timer);
      stream.getTracks().forEach(t => t.stop());
      ctx.close();
      if (reason === "cancel" || reason === "nospeech") {
        setState("idle");
        if (reason === "nospeech") onError("I didn't hear anything.");
        return;
      }
      const blob = new Blob(chunks, { type: recorder.mimeType || type || "audio/webm" });
      setState("transcribing");
      try {
        const r = await fetch(`${apiBase}/api/transcribe${lang ? `?lang=${lang}` : ""}`, {
          method: "POST", headers: { "Content-Type": blob.type }, body: blob,
        });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
        if (data.text) onText(data.text);
        else onError("I didn't catch that, try again.");
      } catch (err) {
        onError(err.message || String(err));
      }
      setState("idle");
    };

    recorder.start();
    setState("listening");
  }

  function startBrowser() {
    const rec = new Recognition();
    rec.lang = LOCALES[lang] || navigator.language || "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    let text = "", cancelled = false;
    rec.onresult = e => { text = Array.from(e.results).map(r => r[0].transcript).join(" ").trim(); };
    rec.onerror = e => {
      if (e.error === "aborted") return;
      onError(e.error === "no-speech" ? "I didn't hear anything."
        : e.error === "not-allowed" ? micError("not-allowed")
        : `Speech recognition error: ${e.error}`);
    };
    rec.onend = () => {
      stop = null;
      setState("idle");
      if (text && !cancelled) onText(text);
    };
    stop = why => {
      cancelled = why === "cancel";
      stop = null;
      cancelled ? rec.abort() : rec.stop();
    };
    rec.start();
    setState("listening");
  }

  return {
    mode,
    get state() { return state; },
    toggle() {
      if (state === "listening") stop?.("manual");
      else if (state === "idle" && mode === "server") startServer();
      else if (state === "idle" && mode === "browser") startBrowser();
    },
    cancel() { stop?.("cancel"); },
  };
}
