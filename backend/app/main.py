import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.catalog import Catalog
from app.citations import CitationResolver
from app.rag import create_engine
from app.routes import chat, files, misc, products, sources, voice
from app.settings import get_settings
from app.transcribe import Transcriber

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.catalog = Catalog.load(settings.products_file, settings.data_dir)
    app.state.resolver = CitationResolver(app.state.catalog)
    app.state.engine = create_engine(settings, app.state.catalog)
    app.state.transcriber = None
    if settings.openai_api_key:
        names = ", ".join(p.name for p in app.state.catalog.products)
        app.state.transcriber = Transcriber(
            settings.openai_api_key, settings.transcribe_model, settings.openai_base_url,
            prompt=f"Domande sui manuali dei robot PUDU: {names}.")
    logging.getLogger("telembot").info(
        "Catalogo caricato: %d prodotti, %d sezioni. Motore RAG: %s. Trascrizione vocale: %s",
        len(app.state.catalog.products), app.state.catalog.section_count, app.state.engine.name,
        settings.transcribe_model if app.state.transcriber else "dal browser (manca OPENAI_API_KEY)")
    yield


app = FastAPI(
    title="Telembot API",
    version="0.1.0",
    description="Accesso conversazionale ai manuali dei robot PUDU: catalogo, fonti, ricerca e chat con citazioni.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

for module in (misc, products, sources, chat, files, voice):
    app.include_router(module.router)


# voice.js e la pagina di prova
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/test", include_in_schema=False)
def test_chat():
    """Pagina di prova per sviluppatori: chat con fonti e figure. Non è l'interfaccia finale."""
    return FileResponse(Path(__file__).parent / "static" / "test_chat.html", media_type="text/html")
