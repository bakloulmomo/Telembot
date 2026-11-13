import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.catalog import Catalog
from app.citations import CitationResolver
from app.rag import create_engine
from app.routes import chat, files, misc, products, sources
from app.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.catalog = Catalog.load(settings.products_file, settings.data_dir)
    app.state.resolver = CitationResolver(app.state.catalog)
    app.state.engine = create_engine(settings, app.state.catalog)
    logging.getLogger("telembot").info(
        "Catalogo caricato: %d prodotti, %d sezioni. Motore RAG: %s",
        len(app.state.catalog.products), app.state.catalog.section_count, app.state.engine.name)
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

for module in (misc, products, sources, chat, files):
    app.include_router(module.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")
