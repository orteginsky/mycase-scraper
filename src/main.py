# src/main.py
"""
Main entry point for the MyCase Scraper API.
Consolidated from api/app.py for standard deployment.
"""
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import HealthCheckResponse, ErrorResponse, DownloadPDFRequest
from src.api.endpoints import pdfs_router, notes_router, messages_router, cases_router, case_stages_router
from src.api.dependencies import (
    check_playwright_profile, 
    check_google_credentials, 
    ConfigValidator,
    validate_mycase_session
)
from src.core import config
from src.core.exceptions import MyCaseScraperError
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MyCase Scraper API",
    description="REST API for scraping data from MyCase and integrating with Google services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(MyCaseScraperError)
async def mycase_exception_handler(request: Request, exc: MyCaseScraperError):
    logger.error("MyCaseScraperError: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=str(exc),
            error_type=type(exc).__name__,
        ).model_dump(),
    )

# Include routers
app.include_router(pdfs_router)
app.include_router(notes_router)
app.include_router(messages_router)
app.include_router(cases_router)
app.include_router(case_stages_router)

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "MyCase Scraper API", "environment": "PROD" if config.IS_PROD else "LOCAL"}

@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check(check_session: bool = False) -> HealthCheckResponse:
    """
    Detailed health check endpoint.
    Returns service status and configuration validation.
    If check_session=true, it performs a live check of the MyCase login.
    """
    res = HealthCheckResponse(
        playwright_profile_exists=check_playwright_profile(),
        google_credentials_configured=check_google_credentials(),
    )
    
    if check_session:
        session_res = validate_mycase_session()
        res.session_active = session_res["session_active"]
        res.session_error = session_res["error"]
        res.user_info = session_res["user_info"]
        
    return res

@app.get("/health/session", response_model=HealthCheckResponse, tags=["Health"])
def session_health_check() -> HealthCheckResponse:
    """
    Direct endpoint for a live session validation.
    Enables quick verification that browser cookies are valid.
    """
    return health_check(check_session=True)

# Legacy / Unificado endpoint (Combining main.py and app.py legacy logic)
@app.post("/download-pdfs", tags=["Main"])
async def download_pdfs_unified(req: DownloadPDFRequest):
    """
    Direct endpoint for downloading PDFs. 
    Maintained for compatibility and ease of use from root.
    """
    from src.api.endpoints.pdfs import download_pdfs_endpoint
    return download_pdfs_endpoint(req)

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing MyCase Scraper API...")
    
    # Sync Playwright profile from GCS if configured
    if config.PW_PROFILE_GCS_BUCKET:
        try:
            from src.core.profile_sync import ensure_profile_available
            if ensure_profile_available():
                logger.info("✅ Playwright profile synced from GCS")
        except Exception as e:
            logger.error("❌ Failed to sync profile: %s", e)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down MyCase Scraper API")

if __name__ == "__main__":
    import uvicorn
    # Use src.main:app if running from project root
    uvicorn.run(
        "src.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.API_RELOAD,
        log_level=config.LOG_LEVEL.lower(),
    )
