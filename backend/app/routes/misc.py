import json
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.catalog import Catalog
from app.routes.deps import get_catalog
from app.schemas import FeedbackRequest, FeedbackResponse, HealthResponse
from app.settings import get_settings

router = APIRouter(prefix="/api", tags=["servizio"])
_feedback_lock = threading.Lock()


@router.get("/health", response_model=HealthResponse, summary="Stato del servizio")
def health(request: Request, catalog: Catalog = Depends(get_catalog)):
    return HealthResponse(status="ok", rag_engine=request.app.state.engine.name,
                          products=len(catalog.products), sections=catalog.section_count,
                          transcription=getattr(request.app.state, "transcriber", None) is not None)


@router.post("/feedback", response_model=FeedbackResponse, status_code=201, summary="Valutazione di una risposta")
def feedback(req: FeedbackRequest):
    path = get_settings().feedback_file
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": datetime.now(timezone.utc).isoformat(), **req.model_dump()}
    with _feedback_lock, path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return FeedbackResponse(ok=True)
