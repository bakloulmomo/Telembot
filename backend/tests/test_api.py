import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.settings import get_settings


@pytest.fixture(scope="module")
def client():
    get_settings().stream_duration_s = 0
    get_settings().mock_delay_s = 0
    with TestClient(app) as c:
        yield c


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


# --- servizio -----------------------------------------------------------------

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["rag_engine"] == "mock"
    assert body["products"] == 22 and body["sections"] > 1000


# --- catalogo -----------------------------------------------------------------

def test_products_list_and_filter(client):
    all_ = client.get("/api/products").json()
    robots = client.get("/api/products", params={"category": "robot"}).json()
    assert len(all_) == 22 and len(robots) == 13
    assert all(p["thumbnail_url"].startswith("/files/") for p in all_)
    flash = next(p for p in all_ if p["id"] == "flashbot")
    assert flash["langs"] == ["en", "de"]


def test_product_detail_specs(client):
    r = client.get("/api/products/bellabot", params={"lang": "it"})
    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "it" and body["spec_section"]["key"] == "2.4"
    specs = {s["key"]: s for s in body["specs"]}
    assert specs["battery_capacity"]["value"] == "25.6 Ah"
    assert specs["battery_capacity"]["label"] == "Capacità batteria"
    assert body["pdf_url"].startswith("/files/bellabot/")
    assert body["spec_tables"][0]["rows"]


def test_product_detail_falls_back_to_english(client):
    body = client.get("/api/products/flashbot", params={"lang": "it"}).json()
    assert body["lang"] == "en"


def test_product_404_and_bad_lang(client):
    assert client.get("/api/products/nope").status_code == 404
    assert client.get("/api/products/bellabot", params={"lang": "fr"}).status_code == 422


def test_compare(client):
    r = client.get("/api/compare", params={"ids": "bellabot,kettybot-pro,holabot", "lang": "it"})
    assert r.status_code == 200
    rows = {row["key"]: row for row in r.json()["rows"]}
    assert rows["battery_capacity"]["values"]["bellabot"] == "25.6 Ah"
    assert set(rows["weight"]["values"]) == {"bellabot", "kettybot-pro", "holabot"}
    assert client.get("/api/compare", params={"ids": "bellabot"}).status_code == 422


# --- fonti e file ---------------------------------------------------------------

def test_source_section_with_images(client):
    r = client.get("/api/sources/bellabot/en/2.3")
    assert r.status_code == 200
    body = r.json()
    assert body["title"].startswith("Appearance") and not body["is_fallback"]
    assert body["image_urls"] and "](/files/bellabot/images/" in body["markdown"]
    assert body["pdf_url"].endswith(f"#page={body['pdf_page']}")
    assert body["prev_key"] == "2.2" and body["next_key"] == "2.4"
    img = client.get(body["image_urls"][0])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"


def test_source_language_fallback(client):
    body = client.get("/api/sources/flashbot/it/2.3").json()
    assert body["lang"] == "en" and body["requested_lang"] == "it" and body["is_fallback"]
    assert client.get("/api/sources/flashbot/it/2.3", params={"fallback": "false"}).status_code == 404


def test_source_duplicate_key(client):
    body = client.get("/api/sources/bellabot/en/5.1~2").json()
    assert body["title"] == "Battery Replacement"


def test_pdf_served(client):
    detail = client.get("/api/products/cc1-dock-base").json()
    r = client.get(detail["pdf_url"])
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"


@pytest.mark.parametrize("path", [
    "/files/bellabot/../../shared/products.json",
    "/files/bellabot/%2e%2e/%2e%2e/backend/.env",
    "/files/bellabot/en.md",
    "/files/bellabot/images/nope.png",
])
def test_files_blocked(client, path):
    assert client.get(path).status_code == 404


# --- ricerca e chat (motore mock) -------------------------------------------------

def test_search(client):
    r = client.post("/api/search", json={"query": "BellaBot battery capacity", "product_ids": ["bellabot"], "lang": "en"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert results and all(h["product_id"] == "bellabot" for h in results)
    assert results[0]["section_id"] == "2.4"
    assert results[0]["source_url"] == "/api/sources/bellabot/en/2.4"


def test_search_unknown_product(client):
    assert client.post("/api/search", json={"query": "x", "product_ids": ["nope"]}).status_code == 422


def test_chat_stream_order(client):
    r = client.post("/api/chat", json={"message": "Qual è la capacità della batteria di BellaBot?",
                                       "product_ids": ["bellabot"]})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    names = [e for e, _ in events]
    assert names[:3] == ["progress"] * 3 and [d["step"] for _, d in events[:3]] == ["search", "read", "check"]
    events = events[3:]
    names = names[3:]
    assert names[0] == "sources" and names[-1] == "done" and "token" in names
    sources = events[0][1]["citations"]
    assert sources and sources[0]["n"] == 1 and sources[0]["product_id"] == "bellabot"
    assert sources[0]["source_url"].startswith("/api/sources/bellabot/it/")
    done = events[-1][1]
    assert done["products"] == ["bellabot"] and done["answer_id"].startswith("a_")


def test_chat_detects_pro_variant(client):
    events = parse_sse(client.post("/api/chat", json={"message": "KettyBot Pro speed"}).text)
    assert events[-1][1]["products"] == ["kettybot-pro"]


def test_chat_validation(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "x", "lang": "fr"}).status_code == 422


def test_chat_engine_error_becomes_sse_error(client):
    engine = app.state.engine

    class Broken:
        name = "broken"

        async def ask(self, *args):
            raise RuntimeError("boom")

    app.state.engine = Broken()
    try:
        events = parse_sse(client.post("/api/chat", json={"message": "ciao"}).text)
    finally:
        app.state.engine = engine
    assert events == [("error", {"code": "rag_error",
                                 "message": "Non è stato possibile generare la risposta. Riprova tra poco."})]


# --- feedback ---------------------------------------------------------------------

def test_feedback(client, tmp_path):
    settings = get_settings()
    original = settings.feedback_file
    settings.feedback_file = tmp_path / "fb.jsonl"
    try:
        r = client.post("/api/feedback", json={"answer_id": "a_123", "rating": "down", "comment": "sbagliato"})
        assert r.status_code == 201
        saved = json.loads(settings.feedback_file.read_text().strip())
        assert saved["rating"] == "down" and saved["answer_id"] == "a_123"
        assert client.post("/api/feedback", json={"answer_id": "a_1", "rating": "meh"}).status_code == 422
    finally:
        settings.feedback_file = original


# --- motore finto: chiarimento, avvisi, figure ----------------------------------

def test_mock_asks_which_model(client):
    events = parse_sse(client.post("/api/chat", json={"message": "How long does BellaBot charge?"}).text)
    sources = next(d for e, d in events if e == "sources")
    done = events[-1][1]
    assert done["status"] == "needs_clarification" and sources["citations"] == []
    assert done["options"] == ["BellaBot", "BellaBot Pro", "Compare both"]
    answer = "".join(d["text"] for e, d in events if e == "token")
    assert answer.startswith("Which BellaBot do you mean?")


def test_mock_answer_after_clarification(client):
    history = [{"role": "user", "content": "How long does BellaBot charge?"},
               {"role": "assistant", "content": "Which BellaBot do you mean?"}]
    events = parse_sse(client.post("/api/chat", json={"message": "BellaBot Pro", "history": history}).text)
    done = events[-1][1]
    assert done["status"] == "answered" and done["products"] == ["bellabot-pro"]


def test_mock_price_gap_note_and_figure(client):
    events = parse_sse(client.post("/api/chat", json={
        "message": "Where is the lidar on the T300 and what does it cost?"}).text)
    done = events[-1][1]
    assert done["gaps"] and "price" in done["gaps"][0]
    citations = next(d for e, d in events if e == "sources")["citations"]
    assert all(c["note"] for c in citations)
    with_figure = [c for c in citations if c["figures"]]
    assert len(with_figure) == 1
    figure = with_figure[0]["figures"][0]
    assert figure["url"].startswith("/files/t300/images/") and figure["labels"]
    assert with_figure[0]["image_urls"] == [figure["url"]]


def test_source_panel_fields(client):
    s = client.get("/api/sources/bellabot/en/1.1").json()
    assert (s["manual_title"], s["category"], s["parent_number"], s["parent_title"]) == \
        ("BellaBot User Manual", "robot", "1", "Safety instructions")
    assert (s["page"], s["pdf_page"], s["pdf_side"], s["pdf_file"]) == \
        (1, 3, "left", "BellaBot_User_Manual-multilanguage.pdf")
    de = client.get("/api/sources/bellabot/de/1.1").json()
    assert de["pdf_side"] in ("left", "right")
