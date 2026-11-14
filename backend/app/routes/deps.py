from fastapi import HTTPException, Request

from app.catalog import Catalog, ProductData
from app.citations import CitationResolver


def get_catalog(request: Request) -> Catalog:
    return request.app.state.catalog


def get_engine(request: Request):
    return request.app.state.engine


def get_resolver(request: Request) -> CitationResolver:
    return request.app.state.resolver


def get_product_or_404(catalog: Catalog, product_id: str) -> ProductData:
    data = catalog.get(product_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Prodotto '{product_id}' inesistente. Vedi GET /api/products.")
    return data
