"""Da audio a testo, per le domande a voce.

Usa l'API di trascrizione di OpenAI (la stessa chiave del motore RAG). Riconosce la
lingua da sola; i nomi dei prodotti vanno nel prompt, così "BellaBot" non diventa
"Bella bot" e "CC1" non diventa "CC uno".
"""

from __future__ import annotations

import httpx

# tipo dell'audio → estensione del file: OpenAI riconosce il formato dal nome
EXTENSIONS = {
    "audio/webm": "webm", "video/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4", "audio/m4a": "m4a",
    "audio/x-m4a": "m4a", "audio/aac": "m4a", "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav",
    "audio/x-wav": "wav", "audio/wave": "wav", "audio/flac": "flac",
}


class Transcriber:
    def __init__(self, api_key: str, model: str, base_url: str, prompt: str = "", timeout_s: float = 30,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.model = model
        self.url = base_url.rstrip("/") + "/audio/transcriptions"
        self.prompt = prompt
        self.client = httpx.AsyncClient(timeout=timeout_s, transport=transport,
                                        headers={"Authorization": f"Bearer {api_key}"})

    async def transcribe(self, audio: bytes, content_type: str, lang: str | None = None) -> str:
        ext = EXTENSIONS.get(content_type, "webm")
        data = {"model": self.model, "response_format": "json"}
        if self.prompt:
            data["prompt"] = self.prompt
        if lang:
            data["language"] = lang
        r = await self.client.post(self.url, data=data, files={"file": (f"audio.{ext}", audio, content_type)})
        r.raise_for_status()
        return str(r.json().get("text") or "").strip()
