# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import logging

from backend.routers import chat
from backend.services.product_loader import load_products

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Ecolite Assistant", version="4.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # ajusta si luego sirves desde otro dominio
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Routers
app.include_router(chat.router)

# Static & SPA
app.mount("/static", StaticFiles(directory="frontend"), name="static")
@app.get("/")
def root():
    return FileResponse("frontend/chatbox.html")

# Health
@app.get("/healthz")
def health():
    return {"ok": True}

# Catálogo: stats para diagnóstico (no expone datos sensibles)
@app.get("/catalog/stats")
def catalog_stats():
    prods, path = load_products()
    return {"count": len(prods), "path": str(path)}

# Manejo global de errores → siempre JSON, con log
@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    # Nota: en producción podrías ocultar detail
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": str(exc)})

# Startup: log de catálogo cargado
@app.on_event("startup")
def on_startup():
    prods, path = load_products()
    logger.info("Catálogo cargado: %d productos desde %s", len(prods), path)
