import logging
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.schemas import TranscribeResponse
from app.settings import get_settings
from app.transcribe import EXTENSIONS

router = APIRouter(prefix="/api", tags=["voce"])
log = logging.getLogger("telembot.voice")


@router.post("/transcribe", response_model=TranscribeResponse, summary="Domanda a voce → testo",
             openapi_extra={"requestBody": {"required": True, "content": {
                 t: {"schema": {"type": "string", "format": "binary"}} for t in ("audio/webm", "audio/mp4", "audio/ogg", "audio/wav")}}})
async def transcribe(request: Request, lang: Literal["en", "de", "it"] | None = None):
    """Il corpo della richiesta è l'audio così com'è (es. il Blob di MediaRecorder), con il suo
    `Content-Type`. Senza `lang` la lingua si riconosce da sola. 503 se manca `OPENAI_API_KEY`:
    in quel caso il frontend usa il riconoscimento vocale del browser."""
    transcriber = getattr(request.app.state, "transcriber", None)
    if transcriber is None:
        raise HTTPException(status_code=503, detail="Trascrizione non configurata: manca OPENAI_API_KEY.")

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Formato audio non supportato: {content_type or 'nessuno'}.")

    max_bytes = int(get_settings().transcribe_max_mb * 1024 * 1024)
    audio = bytearray()
    async for chunk in request.stream():
        audio += chunk
        if len(audio) > max_bytes:
            raise HTTPException(status_code=413, detail="Registrazione troppo lunga.")
    if not audio:
        raise HTTPException(status_code=400, detail="Audio vuoto.")

    try:
        text = await transcriber.transcribe(bytes(audio), content_type, lang)
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Trascrizione non riuscita: %s", exc)
        raise HTTPException(status_code=502, detail="Trascrizione non riuscita. Riprova.") from exc
    return TranscribeResponse(text=text)
