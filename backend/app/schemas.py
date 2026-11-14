"""Modelli dell'API REST. Il contratto con il motore RAG è in app/rag/__init__.py."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Lang = Literal["en", "de", "it"]

class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default=[], max_length=20)
    lang: Lang | Literal["auto"] = "auto"
    product_ids: list[str] = []          # filtro opzionale scelto nell'interfaccia


class FigureLabel(BaseModel):
    n: str | None = None                 # numero del richiamo nella figura, es. "20"
    text: str


class Figure(BaseModel):
    """Una figura del manuale scelta dal motore RAG per questa risposta."""
    id: str | None = None
    url: str
    caption: str | None = None           # didascalia dal manuale: sezione e pagina, mai il testo dell'AI
    page: int | None = None              # pagina PDF della figura (dal nome del file)
    labels: list[FigureLabel] = []       # legenda stampata nel PDF
    description: str | None = None       # descrizione scritta dall'AI: da non mostrare come testo del manuale


class Citation(BaseModel):
    """Una fonte della risposta, già collegata al manuale quando è possibile."""
    n: int                               # numero usato nel testo: [1], [2] …
    label: str                           # es. "BellaBot · 2.4 Specifications"
    text: str                            # testo della sezione del manuale (senza figure né testi AI), o del chunk
    product_id: str | None = None
    product_name: str | None = None
    category: Literal["robot", "accessory"] | None = None
    document: str | None = None          # es. "BellaBot User Manual"
    lang: Lang | None = None
    section_id: str | None = None
    section_title: str | None = None
    section_path: str | None = None      # es. "1. Safety instructions › 1.1 Power usage"
    page: int | None = None              # pagina stampata
    pdf_page: int | None = None          # pagina del PDF originale
    page_side: Literal["left", "right"] | None = None   # colonna della pagina del PDF
    pdf_file: str | None = None
    score: float | None = None
    source_url: str | None = None        # /api/sources/… se la sezione è stata riconosciuta
    pdf_url: str | None = None
    image_urls: list[str] = []
    figures: list[Figure] = []           # solo le figure scelte dal RAG, con la legenda
    note: str | None = None              # come la risposta usa questa fonte (scritto dal modello)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    rag_engine: str
    products: int
    sections: int
    transcription: bool = False          # True se POST /api/transcribe è configurato


class TranscribeResponse(BaseModel):
    text: str


class SpecValue(BaseModel):
    key: str                 # chiave normalizzata, es. "battery_capacity"
    label: str               # etichetta nella lingua richiesta
    value: str               # valore come scritto nel manuale


class ProductSummary(BaseModel):
    id: str
    name: str
    category: Literal["robot", "accessory"]
    langs: list[Lang]
    overview: str | None     # primo paragrafo della panoramica, nella lingua richiesta se c'è
    overview_lang: Lang | None
    thumbnail_url: str | None
    key_specs: list[SpecValue]


class SectionRef(BaseModel):
    key: str
    number: str | None
    title: str
    level: int
    page: int | None
    source_url: str


class SpecTable(BaseModel):
    header: list[str] | None
    rows: list[list[str]]


class ProductDetail(ProductSummary):
    lang: Lang               # lingua delle sezioni e delle tabelle restituite
    pdf_url: str | None
    sections: list[SectionRef]
    spec_section: SectionRef | None
    spec_tables: list[SpecTable]
    specs: list[SpecValue]   # specifiche normalizzate (dal manuale inglese)


class SourceSection(BaseModel):
    product_id: str
    product_name: str
    lang: Lang               # lingua effettiva del testo
    requested_lang: Lang
    is_fallback: bool        # True se la sezione non esiste nella lingua richiesta
    key: str
    number: str | None
    title: str
    page: int | None
    page_end: int | None
    pdf_page: int | None
    pdf_url: str | None      # PDF originale, già posizionato sulla pagina
    pdf_side: Literal["left", "right"] | None = None   # colonna della pagina del PDF
    pdf_file: str | None = None       # nome del PDF originale
    manual_title: str = ""            # es. "BellaBot User Manual"
    category: Literal["robot", "accessory"] = "robot"
    parent_number: str | None = None  # sezione che la contiene, es. "1" per la 1.1
    parent_title: str | None = None
    markdown: str            # con gli URL delle immagini già riscritti
    image_urls: list[str]
    available_langs: list[Lang]
    prev_key: str | None
    next_key: str | None


class CompareProduct(BaseModel):
    id: str
    name: str
    category: Literal["robot", "accessory"]


class CompareRow(BaseModel):
    key: str
    label: str
    values: dict[str, str | None]   # product_id → valore


class CompareResponse(BaseModel):
    products: list[CompareProduct]
    rows: list[CompareRow]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    product_ids: list[str] = []
    lang: Lang | None = None
    k: int = Field(default=8, ge=1, le=30)


class SearchResponse(BaseModel):
    query: str
    rag_engine: str
    results: list[Citation]


class FeedbackRequest(BaseModel):
    answer_id: str = Field(min_length=1, max_length=64)
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=2000)
    question: str | None = Field(default=None, max_length=2000)
    answer: str | None = Field(default=None, max_length=20000)


class FeedbackResponse(BaseModel):
    ok: bool
