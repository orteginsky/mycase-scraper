# api/endpoints/__init__.py
"""
FastAPI router endpoints for MyCase scraping tasks.
"""
from src.api.endpoints.pdfs import router as pdfs_router
from src.api.endpoints.notes import router as notes_router
from src.api.endpoints.messages import router as messages_router
from src.api.endpoints.cases import router as cases_router
from src.api.endpoints.case_stages import router as case_stages_router

__all__ = ["pdfs_router", "notes_router", "messages_router", "cases_router", "case_stages_router"]
