"""Domande a voce: POST /api/transcribe e voice.js."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.settings import get_settings
from app.transcribe import Transcriber

AUDIO = b"\x1aE\xdf\xa3fake-webm-audio"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def use_transcriber(client):
    original = app.state.transcriber

    def swap(handler):
        transport = httpx.MockTransport(handler) if handler else None
        app.state.transcriber = Transcriber("sk-test", "gpt-4o-mini-transcribe", "https://api.test/v1",
                                            prompt="PUDU: BellaBot, CC1", transport=transport) if handler else None
    yield swap
    app.state.transcriber = original


def test_not_configured_returns_503(client, use_transcriber):
    use_transcriber(None)
    assert client.get("/api/health").json()["transcription"] is False
    r = client.post("/api/transcribe", content=AUDIO, headers={"Content-Type": "audio/webm"})
    assert r.status_code == 503


def test_transcribe_ok(client, use_transcriber):
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.read()
        return httpx.Response(200, json={"text": "  Quanto pesa il CC1?  "})

    use_transcriber(handler)
    assert client.get("/api/health").json()["transcription"] is True
    r = client.post("/api/transcribe?lang=it", content=AUDIO,
                    headers={"Content-Type": "audio/webm;codecs=opus"})
    assert r.status_code == 200
    assert r.json() == {"text": "Quanto pesa il CC1?"}
    assert seen["url"] == "https://api.test/v1/audio/transcriptions"
    assert seen["auth"] == "Bearer sk-test"
    body = seen["body"]
    assert b'filename="audio.webm"' in body and AUDIO in body
    assert b"gpt-4o-mini-transcribe" in body and b"BellaBot" in body
    assert b'name="language"' in body and b"\r\n\r\nit\r\n" in body


def test_safari_mp4_gets_mp4_filename(client, use_transcriber):
    names = []
    use_transcriber(lambda req: names.append(req.read()) or httpx.Response(200, json={"text": "Hi"}))
    assert client.post("/api/transcribe", content=AUDIO, headers={"Content-Type": "audio/mp4"}).status_code == 200
    assert b'filename="audio.mp4"' in names[0] and b'name="language"' not in names[0]


@pytest.mark.parametrize("content, ctype, status", [
    (AUDIO, "text/plain", 415),
    (AUDIO, "", 415),
    (b"", "audio/webm", 400),
])
def test_bad_requests(client, use_transcriber, content, ctype, status):
    use_transcriber(lambda req: httpx.Response(200, json={"text": "x"}))
    headers = {"Content-Type": ctype} if ctype else {}
    assert client.post("/api/transcribe", content=content, headers=headers).status_code == status


def test_too_large(client, use_transcriber):
    use_transcriber(lambda req: httpx.Response(200, json={"text": "x"}))
    settings = get_settings()
    original, settings.transcribe_max_mb = settings.transcribe_max_mb, 0.001
    try:
        r = client.post("/api/transcribe", content=b"0" * 5000, headers={"Content-Type": "audio/webm"})
    finally:
        settings.transcribe_max_mb = original
    assert r.status_code == 413


def test_upstream_error_becomes_502(client, use_transcriber):
    use_transcriber(lambda req: httpx.Response(500, json={"error": "boom"}))
    r = client.post("/api/transcribe", content=AUDIO, headers={"Content-Type": "audio/webm"})
    assert r.status_code == 502


def test_voice_js_and_test_page_served(client):
    r = client.get("/static/voice.js")
    assert r.status_code == 200 and "createVoiceInput" in r.text
    assert 'id="mic"' in client.get("/test").text
