# backend/routers/admin.py
from fastapi import APIRouter
from backend.services.product_loader import reload_products
from backend.services.search_service import reset_index

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/reload")
def reload_catalog():
    prods, path = reload_products()
    reset_index()
    return {"ok": True, "count": len(prods), "path": str(path)}
