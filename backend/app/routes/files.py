from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.catalog import Catalog
from app.routes.deps import get_catalog, get_product_or_404

router = APIRouter(tags=["file"])

ALLOWED = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".pdf": "application/pdf"}


@router.get("/files/{product_id}/{file_path:path}", summary="Immagini e PDF dei manuali")
def get_file(product_id: str, file_path: str, catalog: Catalog = Depends(get_catalog)):
    data = get_product_or_404(catalog, product_id)
    root = data.product.path.resolve()
    target = (root / file_path).resolve()
    media_type = ALLOWED.get(target.suffix.lower())
    if not target.is_relative_to(root) or media_type is None or not target.is_file():
        raise HTTPException(status_code=404, detail="File non trovato.")
    return FileResponse(target, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"},
                        content_disposition_type="inline")
