from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.exceptions import (
    TixBaseException,
    tix_exception_handler,
    unhandled_exception_handler,
)
from app.api.v1 import api_router

settings = get_settings()
setup_logging(debug=settings.app_debug)

app = FastAPI(
    title="Tix API",
    description="AI-powered customer support platform",
    version="0.1.0",
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
)

# CORS — tighten origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(TixBaseException, tix_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routes
app.include_router(api_router)