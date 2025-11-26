# api/app.py
"""
Main FastAPI application for MyCase scraping service.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import HealthCheckResponse, ErrorResponse
from api.endpoints import pdfs_router, notes_router, messages_router
from api.dependencies import check_playwright_profile, check_google_credentials, ConfigValidator
from core import config
from core.exceptions import MyCaseScraperError
from utils.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MyCase Scraper API",
    description="REST API for scraping data from MyCase and integrating with Google services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (configure as needed for your deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for custom exceptions
@app.exception_handler(MyCaseScraperError)
async def mycase_exception_handler(request: Request, exc: MyCaseScraperError):
    """Handle all custom MyCaseScraperError exceptions."""
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


@app.get("/", tags=["Health"])
def root():
    """Root endpoint - basic health check."""
    return {"status": "ok", "service": "MyCase Scraper API"}


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check() -> HealthCheckResponse:
    """
    Detailed health check endpoint.
    Returns service status and configuration validation.
    """
    return HealthCheckResponse(
        playwright_profile_exists=check_playwright_profile(),
        google_credentials_configured=check_google_credentials(),
    )


@app.get("/config/validate", tags=["Health"])
def validate_config():
    """
    Validate all configuration.
    Useful for debugging deployment issues.
    """
    return ConfigValidator.validate_all()


# Legacy endpoint for backward compatibility
@app.post("/download-pdfs", tags=["Legacy"], include_in_schema=False)
async def download_pdfs_legacy(request: Request):
    """
    Legacy endpoint - redirects to new /pdfs/download.
    Maintained for backward compatibility with existing Apps Script.
    """
    from api.endpoints.pdfs import download_pdfs_endpoint
    from api.schemas import DownloadPDFRequest

    body = await request.json()
    req = DownloadPDFRequest(**body)
    return download_pdfs_endpoint(req)


# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting MyCase Scraper API")
    logger.info("Download directory: %s", config.DOWNLOAD_DIR)
    logger.info("Playwright profile: %s", config.PW_USER_DATA_DIR)
    logger.info("Headless mode: %s", config.PW_HEADLESS)

    # Validate configuration
    validation = ConfigValidator.validate_all()
    if not validation["all_valid"]:
        logger.warning("Configuration issues detected:")
        for key, result in validation.items():
            if isinstance(result, dict) and not result.get("valid", True):
                for issue in result.get("issues", []):
                    logger.warning("  - %s", issue)

    # Sync Playwright profile from GCS (for Cloud Run)
    if config.PW_PROFILE_GCS_BUCKET:
        try:
            from core.profile_sync import ensure_profile_available

            logger.info("=" * 60)
            logger.info("Profile Sync Configuration:")
            logger.info("  GCS Bucket: %s", config.PW_PROFILE_GCS_BUCKET)
            logger.info("  GCS Prefix: %s", config.PW_PROFILE_GCS_PREFIX)
            logger.info("  Local Profile Dir: %s", config.PW_USER_DATA_DIR)
            logger.info("=" * 60)

            logger.info("Attempting to sync Playwright profile from GCS...")
            if ensure_profile_available():
                logger.info("✅ Playwright profile synced from GCS successfully")

                # Verify profile has content
                profile_files = list(config.PW_USER_DATA_DIR.rglob("*"))
                logger.info("Profile contains %d files/directories", len(profile_files))

                # Check for critical session files (Chrome moved cookies to Network subfolder)
                cookies_paths = [
                    config.PW_USER_DATA_DIR / "Default" / "Network" / "Cookies",
                    config.PW_USER_DATA_DIR / "Default" / "Cookies",
                ]
                cookies_exist = any(p.exists() for p in cookies_paths)
                local_storage_exists = (config.PW_USER_DATA_DIR / "Default" / "Local Storage").exists()
                logger.info("  Cookies file exists: %s", cookies_exist)
                logger.info("  Local Storage exists: %s", local_storage_exists)

                if not cookies_exist:
                    logger.warning("⚠️  No cookies found - authentication may be required")
            else:
                logger.warning("⚠️  No profile found in GCS")
                logger.warning("Authentication will be required on first request")
                logger.warning("To fix:")
                logger.warning("  1. Run: python scripts/seed_playwright_profile.py")
                logger.warning("  2. Run: python scripts/upload_profile_to_gcs.py")
        except Exception as e:
            logger.error("❌ Failed to sync profile from GCS: %s", e)
            logger.error("Service will attempt to authenticate on first request")
    else:
        logger.info("Profile sync disabled (PW_PROFILE_GCS_BUCKET not configured)")
        logger.info("Using local profile only")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down MyCase Scraper API")


# Entry point for running directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.API_RELOAD,
        log_level=config.LOG_LEVEL.lower(),
    )
