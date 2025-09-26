# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import logging

from backend.routers import chat
from backend.routers import admin
from backend.services.product_loader import load_products

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Ecolite Assistant", version="4.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(chat.router)
app.include_router(admin.router)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def root():
    return FileResponse("frontend/chatbox.html")

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/catalog/stats")
def catalog_stats():
    prods, path = load_products()
    return {"count": len(prods), "path": str(path)}

@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": str(exc)})

@app.on_event("startup")
def on_startup():
    prods, path = load_products()
    logger.info("Catálogo cargado: %d productos desde %s", len(prods), path)
