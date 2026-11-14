from fastapi import APIRouter, Depends, HTTPException

from app.catalog import Catalog
from app.routes.deps import get_catalog, get_product_or_404
from app.schemas import Lang, SourceSection

router = APIRouter(prefix="/api", tags=["fonti"])


@router.get("/sources/{product_id}/{lang}/{key}", response_model=SourceSection,
            summary="Testo di una sezione del manuale (ciò che si apre cliccando una citazione)")
def get_source(product_id: str, lang: Lang, key: str, fallback: bool = True,
               catalog: Catalog = Depends(get_catalog)):
    """Con `fallback=true` (predefinito), se la sezione non esiste nella lingua richiesta
    restituisce la versione inglese e imposta `is_fallback`."""
    data = get_product_or_404(catalog, product_id)
    manual = data.manuals.get(lang)
    section = manual.get(key) if manual else None
    if section is None and fallback and lang != "en":
        manual = data.manuals["en"]
        section = manual.get(key)
    if section is None:
        raise HTTPException(status_code=404,
                            detail=f"Sezione '{key}' non trovata nel manuale {data.product.name} ({lang}).")

    idx = manual.sections.index(section)
    parent_number = section.number.rsplit(".", 1)[0] if section.number and "." in section.number else None
    parent = manual.get(parent_number) if parent_number else None
    return SourceSection(
        product_id=product_id,
        product_name=data.product.name,
        lang=manual.lang,
        requested_lang=lang,
        is_fallback=manual.lang != lang,
        key=section.key,
        number=section.number,
        title=section.title,
        page=section.page,
        page_end=section.page_end,
        pdf_page=section.pdf_page,
        pdf_url=catalog.pdf_url(product_id, manual, section.pdf_page),
        pdf_side=section.pdf_side,
        pdf_file=manual.source_pdf,
        manual_title=manual.meta.get("title") or f"{data.product.name} User Manual",
        category=data.product.category,
        parent_number=parent.number if parent else None,
        parent_title=parent.title if parent else None,
        markdown=catalog.rewrite_images(product_id, section.markdown),
        image_urls=[catalog.file_url(product_id, img) for img in section.images],
        available_langs=[lg for lg, m in data.manuals.items() if m.get(key)],
        prev_key=manual.sections[idx - 1].key if idx > 0 else None,
        next_key=manual.sections[idx + 1].key if idx + 1 < len(manual.sections) else None,
    )
