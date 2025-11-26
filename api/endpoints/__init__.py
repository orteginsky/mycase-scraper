# api/endpoints/__init__.py
"""
FastAPI router endpoints for MyCase scraping tasks.
"""
from api.endpoints.pdfs import router as pdfs_router
from api.endpoints.notes import router as notes_router
from api.endpoints.messages import router as messages_router

__all__ = ["pdfs_router", "notes_router", "messages_router"]
