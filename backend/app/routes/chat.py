"""Chat e ricerca: il backend fa da tramite verso il motore RAG.

Il RAG restituisce la risposta completa; il backend la invia al frontend come
stream SSE, sempre in quest'ordine:
    sources → token (uno o più) → done        oppure, se il RAG fallisce, error.
"""

import asyncio
import inspect
import json
import logging
import re
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.catalog import Catalog
from app.citations import CitationResolver
from app.routes.deps import get_catalog, get_engine, get_resolver
from app.schemas import ChatRequest, SearchRequest, SearchResponse
from app.settings import get_settings

log = logging.getLogger("telembot.chat")
router = APIRouter(prefix="/api", tags=["chat"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _progress_event(ev) -> dict:
    """Solo campi testuali brevi: il motore decide cosa dire, il frontend lo mostra."""
    ev = ev if isinstance(ev, dict) else {"detail": str(ev)}
    return {"step": str(ev.get("step") or "")[:40], "detail": str(ev.get("detail") or "")[:300]}


def _check_products(catalog: Catalog, product_ids: list[str]) -> None:
    unknown = [pid for pid in product_ids if catalog.get(pid) is None]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Prodotti inesistenti: {unknown}")


@router.post("/search", response_model=SearchResponse, summary="Solo retrieval (API pubblica)")
async def search(req: SearchRequest, catalog: Catalog = Depends(get_catalog),
                 resolver: CitationResolver = Depends(get_resolver), engine=Depends(get_engine)):
    _check_products(catalog, req.product_ids)
    if getattr(engine, "search", None) is None:
        raise HTTPException(status_code=501, detail="Il motore RAG collegato non espone la ricerca.")
    sources = await asyncio.wait_for(engine.search(req.query, req.product_ids, req.lang, req.k),
                                     timeout=get_settings().rag_timeout_s)
    return SearchResponse(query=req.query, rag_engine=engine.name,
                          results=[resolver.resolve(s, i) for i, s in enumerate(sources, start=1)])


@router.post("/chat", summary="Risposta in streaming SSE con fonti",
             response_class=StreamingResponse,
             responses={200: {"content": {"text/event-stream": {}},
                              "description": "Eventi `progress` (facoltativi), `sources`, `token`, `done` oppure `error`."}})
async def chat(req: ChatRequest, catalog: Catalog = Depends(get_catalog),
               resolver: CitationResolver = Depends(get_resolver), engine=Depends(get_engine)):
    _check_products(catalog, req.product_ids)
    settings = get_settings()
    answer_id = f"a_{uuid.uuid4().hex[:12]}"

    async def stream():
        start = time.perf_counter()
        args = (req.message, [h.model_dump() for h in req.history],
                None if req.lang == "auto" else req.lang, req.product_ids)
        # Se il motore accetta `progress`, i suoi passi arrivano al frontend come eventi "progress".
        events: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        kwargs = {}
        if "progress" in inspect.signature(engine.ask).parameters:
            kwargs["progress"] = lambda ev: loop.call_soon_threadsafe(events.put_nowait, ev)
        task = asyncio.create_task(asyncio.wait_for(engine.ask(*args, **kwargs), timeout=settings.rag_timeout_s))
        try:
            while not task.done():
                getter = asyncio.create_task(events.get())
                await asyncio.wait({task, getter}, return_when=asyncio.FIRST_COMPLETED)
                if getter.done():
                    yield sse("progress", _progress_event(getter.result()))
                else:
                    getter.cancel()
            while not events.empty():
                yield sse("progress", _progress_event(events.get_nowait()))
            result = task.result()
        except asyncio.TimeoutError:
            log.warning("RAG timeout answer_id=%s", answer_id)
            yield sse("error", {"code": "rag_timeout",
                                "message": "Il motore di ricerca non ha risposto in tempo. Riprova."})
            return
        except Exception:
            log.exception("RAG error answer_id=%s", answer_id)
            yield sse("error", {"code": "rag_error",
                                "message": "Non è stato possibile generare la risposta. Riprova tra poco."})
            return
        finally:
            if not task.done():      # il client ha chiuso la connessione (es. "Stop")
                task.cancel()

        citations = [resolver.resolve(s, i) for i, s in enumerate(result.sources, start=1)]
        yield sse("sources", {"citations": [c.model_dump() for c in citations]})

        # la risposta arriva intera: la si manda a pezzi per l'effetto "scrittura", entro stream_duration_s
        pieces = re.findall(r"\S+\s*", result.answer) or [result.answer]
        pieces = ["".join(pieces[i:i + 3]) for i in range(0, len(pieces), 3)]
        delay = settings.stream_duration_s / len(pieces) if settings.stream_duration_s else 0
        for piece in pieces:
            yield sse("token", {"text": piece})
            if delay:
                await asyncio.sleep(delay)

        products = list(dict.fromkeys(c.product_id for c in citations if c.product_id))
        latency_ms = round((time.perf_counter() - start) * 1000)
        log.info("answer_id=%s products=%s sources=%d latency_ms=%d q=%r",
                 answer_id, products, len(citations), latency_ms, req.message[:200])
        yield sse("done", {"answer_id": answer_id, "products": products, "latency_ms": latency_ms,
                           "status": result.status, "language": result.language,
                           "gaps": result.gaps, "options": result.options})

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)
