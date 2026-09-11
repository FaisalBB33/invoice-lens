from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, extract, health, invoices, ocr, upload
from app.core.config import settings

app = FastAPI(
    title="AI Invoice Processing API",
    description="Phase 5 API: extract, persist, and chat with saved invoice data.",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(upload.router)
app.include_router(ocr.router)
app.include_router(extract.router)
app.include_router(invoices.router)
app.include_router(chat.router)
