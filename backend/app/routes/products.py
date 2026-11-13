from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.catalog import KEY_SPECS, SPEC_FIELDS, SPEC_LABELS, Catalog, ProductData
from app.routes.deps import get_catalog, get_product_or_404
from app.schemas import (CompareProduct, CompareResponse, CompareRow, Lang, ProductDetail, ProductSummary,
                         SectionRef, SpecTable, SpecValue)

router = APIRouter(prefix="/api", tags=["catalogo"])


def _summary(catalog: Catalog, data: ProductData, lang: str) -> dict:
    p = data.product
    manual = data.manual(lang)
    overview = catalog.overview(manual)
    overview_lang = manual.lang if overview else None
    if overview is None and manual.lang != "en":
        overview = catalog.overview(data.manuals["en"])
        overview_lang = "en" if overview else None
    thumb = catalog.thumbnail(data.manuals["en"])
    return dict(
        id=p.id, name=p.name, category=p.category, langs=p.langs,
        overview=overview, overview_lang=overview_lang,
        thumbnail_url=catalog.file_url(p.id, thumb) if thumb else None,
        key_specs=[SpecValue(key=k, label=lbl, value=v) for k, lbl, v in catalog.localized_specs(data, lang, KEY_SPECS)][:5],
    )


@router.get("/products", response_model=list[ProductSummary], summary="Elenco dei prodotti")
def list_products(
    category: Literal["robot", "accessory"] | None = None,
    lang: Lang = "en",
    catalog: Catalog = Depends(get_catalog),
):
    return [_summary(catalog, d, lang) for d in catalog.by_id.values()
            if category is None or d.product.category == category]


@router.get("/products/{product_id}", response_model=ProductDetail, summary="Scheda prodotto")
def get_product(product_id: str, lang: Lang = "en", catalog: Catalog = Depends(get_catalog)):
    data = get_product_or_404(catalog, product_id)
    manual = data.manual(lang)

    def ref(s) -> SectionRef:
        return SectionRef(key=s.key, number=s.number, title=s.title, level=s.level, page=s.page,
                          source_url=catalog.source_url(product_id, manual.lang, s.key))

    spec_section = catalog.spec_section(manual)
    return ProductDetail(
        **_summary(catalog, data, lang),
        lang=manual.lang,
        pdf_url=catalog.pdf_url(product_id, manual),
        sections=[ref(s) for s in manual.sections],
        spec_section=ref(spec_section) if spec_section else None,
        spec_tables=[SpecTable(header=h, rows=r) for h, r in catalog.spec_tables(spec_section)],
        specs=[SpecValue(key=k, label=lbl, value=v) for k, lbl, v in catalog.localized_specs(data, lang)],
    )


@router.get("/compare", response_model=CompareResponse, summary="Confronto delle specifiche")
def compare(
    ids: str = Query(description="Da 2 a 4 id separati da virgola", examples=["bellabot,kettybot-pro,holabot"]),
    lang: Lang = "en",
    catalog: Catalog = Depends(get_catalog),
):
    product_ids = list(dict.fromkeys(i.strip() for i in ids.split(",") if i.strip()))
    if not 2 <= len(product_ids) <= 4:
        raise HTTPException(status_code=422, detail="Indica da 2 a 4 prodotti, es. ?ids=bellabot,holabot")
    items = [get_product_or_404(catalog, pid) for pid in product_ids]
    rows = []
    for key, _, labels in SPEC_FIELDS:
        values = {d.product.id: d.specs.get(key) for d in items}
        if any(values.values()):
            rows.append(CompareRow(key=key, label=SPEC_LABELS[key].get(lang, labels["en"]), values=values))
    return CompareResponse(
        products=[CompareProduct(id=d.product.id, name=d.product.name, category=d.product.category) for d in items],
        rows=rows,
    )
