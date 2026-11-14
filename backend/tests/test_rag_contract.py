"""Il contratto minimo con il RAG: formati accettati e riconoscimento delle fonti."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import normalize_result
from app.rag.adapters import HttpRag, PythonRag
from app.settings import get_settings


@pytest.fixture(scope="module")
def client():
    get_settings().stream_duration_s = 0
    with TestClient(app) as c:
        yield c


@pytest.fixture
def use_engine(client):
    original = app.state.engine

    def swap(engine):
        app.state.engine = engine
    yield swap
    app.state.engine = original


def chat_events(client, message="domanda"):
    text = client.post("/api/chat", json={"message": message}).text
    return [(b.split("\n")[0][7:], json.loads(b.split("\n")[1][6:])) for b in text.strip().split("\n\n")]


# --- normalizzazione dei formati -------------------------------------------------

@pytest.mark.parametrize("raw, answer, n_sources", [
    ("solo testo", "solo testo", 0),
    ({"answer": "a", "sources": ["s1", "s2"]}, "a", 2),
    ({"response": "a", "source_nodes": [{"node": {"text": "t", "metadata": {"file": "x.md"}}, "score": 0.5}]}, "a", 1),
    ({"output": "a", "context": [{"page_content": "t", "metadata": {"source": "en.md"}}]}, "a", 1),
    (("a", [{"content": "t"}]), "a", 1),
    (SimpleNamespace(response="a", source_nodes=[SimpleNamespace(node=SimpleNamespace(text="t", metadata={}), score=1)]), "a", 1),
])
def test_normalize_formats(raw, answer, n_sources):
    result = normalize_result(raw)
    assert result.answer == answer and len(result.sources) == n_sources
    assert all("text" in s for s in result.sources)


def test_normalize_flattens_metadata():
    src = normalize_result({"answer": "a", "sources": [{"page_content": "t", "metadata": {"source": "f.md", "page": 3}}]}).sources[0]
    assert src == {"source": "f.md", "page": 3, "page_content": "t", "text": "t"}


# --- riconoscimento delle fonti ----------------------------------------------------

def test_resolve_from_path_and_text(client):
    r = app.state.resolver
    c = r.resolve({"text": "| Battery capacity | 25.6 Ah |", "source": "data/manuals/BellaBot_User_Manual-multilanguage/en.md"}, 1)
    assert (c.product_id, c.lang, c.section_id) == ("bellabot", "en", "2.4")
    assert c.label == "BellaBot · 2.4 Specifications" and c.source_url == "/api/sources/bellabot/en/2.4"


def test_resolve_from_text_only(client):
    section = app.state.catalog.get("kettybot-pro").manuals["de"].get("2.4")
    chunk = section.markdown[100:400]              # un pezzo qualsiasi, senza metadati
    c = app.state.resolver.resolve({"text": chunk}, 2)
    assert (c.product_id, c.lang, c.section_id) == ("kettybot-pro", "de", "2.4")


def test_resolve_with_explicit_ids(client):
    c = app.state.resolver.resolve({"text": "", "product_id": "holabot", "lang": "it", "section_id": "2.4"}, 1)
    assert c.source_url == "/api/sources/holabot/it/2.4" and c.pdf_url.startswith("/files/holabot/")


def test_resolve_unknown_source_still_shown(client):
    c = app.state.resolver.resolve({"text": "testo inventato", "source": "/tmp/altro/documento.txt"}, 3)
    assert c.product_id is None and c.source_url is None and c.label == "documento.txt"


# --- motori collegati ----------------------------------------------------------------

def test_python_engine_plain_string(client, use_engine):
    use_engine(PythonRag("tests.fake_rag:answer_plain"))
    events = chat_events(client)
    assert events[0] == ("sources", {"citations": []})
    assert "".join(d["text"] for e, d in events if e == "token") == "Solo testo, senza fonti."
    assert events[-1][0] == "done"


def test_python_engine_langchain_shape(client, use_engine):
    use_engine(PythonRag("tests.fake_rag:answer_langchain"))
    client.post("/api/chat", json={"message": "x", "lang": "it"})
    events = chat_events(client)
    cit = events[0][1]["citations"][0]
    assert (cit["product_id"], cit["section_id"], cit["lang"]) == ("bellabot", "2.4", "en")
    assert events[-1][1]["products"] == ["bellabot"]


def test_python_engine_async_tuple_and_no_search(client, use_engine):
    use_engine(PythonRag("tests.fake_rag:answer_async"))
    cit = chat_events(client)[0][1]["citations"][0]
    assert cit["label"] == "Fonte 1" and cit["product_id"] is None
    assert client.post("/api/search", json={"query": "x"}).status_code == 501


def test_python_engine_search(client, use_engine):
    use_engine(PythonRag("tests.fake_rag:answer_plain", "tests.fake_rag:search"))
    hit = client.post("/api/search", json={"query": "battery"}).json()["results"][0]
    assert hit["product_id"] == "bellabot" and hit["score"] == 0.91 and hit["section_id"] == "2.4"


def test_http_engine(client, use_engine):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"answer": "Dal servizio [1]",
                                         "sources": [{"text": "| Battery capacity | 25.6 Ah |", "product_id": "bellabot"}]})

    use_engine(HttpRag("http://rag.test/ask", transport=httpx.MockTransport(handler)))
    events = chat_events(client, "Batteria di BellaBot?")
    assert seen == {"question": "Batteria di BellaBot?", "history": [], "lang": None, "product_ids": []}
    assert events[0][1]["citations"][0]["section_id"] == "2.4"


def test_http_engine_failure_becomes_error_event(client, use_engine):
    use_engine(HttpRag("http://rag.test/ask", transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    assert chat_events(client)[0][0] == "error"


def test_engine_timeout(client, use_engine):
    class Slow:
        name = "slow"
        search = None

        async def ask(self, *a):
            await asyncio.sleep(5)

    settings = get_settings()
    original, settings.rag_timeout_s = settings.rag_timeout_s, 0.05
    use_engine(Slow())
    try:
        assert chat_events(client)[0] == ("error", {"code": "rag_timeout",
                                                     "message": "Il motore di ricerca non ha risposto in tempo. Riprova."})
    finally:
        settings.rag_timeout_s = original


def test_resolve_ambiguous_text_gets_no_product(client):
    # riga identica in sei manuali (BellaBot, KettyBot, HolaBot…): senza altri indizi non si sceglie a caso
    c = app.state.resolver.resolve({"text": "| Microphone | 6-mic circular array kit |"}, 1)
    assert c.product_id is None and c.source_url is None
