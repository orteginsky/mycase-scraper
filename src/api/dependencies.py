# api/dependencies.py
"""
FastAPI dependency injection utilities.
Provides shared resources and validates configuration.
"""
from pathlib import Path
from fastapi import Depends, HTTPException, status

from src.core import config
from src.core import mycase_session, check_session_active, mycase_auto_session
from src.utils.logger import get_logger

logger = get_logger(__name__)


def check_playwright_profile() -> bool:
    """
    Check if Playwright browser profile directory exists.
    Used for health checks.

    Returns:
        True if profile directory exists
    """
    return config.PW_USER_DATA_DIR.exists()


def check_google_credentials() -> bool:
    """
    Check if Google credentials are configured.
    Used for health checks.

    Returns:
        True if credentials file or JSON is configured
    """
    if config.SA_JSON:
        return True
    if config.GOOGLE_APPLICATION_CREDENTIALS:
        return Path(config.GOOGLE_APPLICATION_CREDENTIALS).exists()
    return False


def require_google_credentials():
    """
    Dependency that ensures Google credentials are configured.
    Raises HTTPException if not configured.
    """
    if not check_google_credentials():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS or SA_JSON.",
        )
    return True


def require_mycase_credentials():
    """
    Dependency that ensures MyCase credentials are configured.
    Raises HTTPException if not configured.
    """
    if not config.MYCASE_EMAIL or not config.MYCASE_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MyCase credentials not configured. Set MYCASE_EMAIL and MYCASE_PASSWORD.",
        )
    return True


def require_drive_folder():
    """
    Dependency that ensures a default Drive folder is configured.
    """
    if not config.DRIVE_DEFAULT_FOLDER_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Default Drive folder not configured. Set DRIVE_DEFAULT_FOLDER_ID.",
        )
    return config.DRIVE_DEFAULT_FOLDER_ID


class ConfigValidator:
    """
    Validates that required configuration is present.
    Can be used as a dependency or called directly.
    """

    @staticmethod
    def validate_scraping() -> dict:
        """Validate configuration required for scraping."""
        issues = []

        if not config.MYCASE_EMAIL:
            issues.append("MYCASE_EMAIL not set")
        if not config.MYCASE_PASSWORD:
            issues.append("MYCASE_PASSWORD not set")
        if not config.PW_USER_DATA_DIR.exists():
            issues.append(f"Playwright profile directory does not exist: {config.PW_USER_DATA_DIR}")
        if not config.DOWNLOAD_DIR.exists():
            issues.append(f"Download directory does not exist: {config.DOWNLOAD_DIR}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def validate_google() -> dict:
        """Validate Google Cloud configuration."""
        issues = []

        if not config.SA_JSON and not config.GOOGLE_APPLICATION_CREDENTIALS:
            issues.append("No Google credentials configured (SA_JSON or GOOGLE_APPLICATION_CREDENTIALS)")
        elif config.GOOGLE_APPLICATION_CREDENTIALS and not Path(config.GOOGLE_APPLICATION_CREDENTIALS).exists():
            issues.append(f"Credentials file not found: {config.GOOGLE_APPLICATION_CREDENTIALS}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def validate_cloud_run() -> dict:
        """Validate Cloud Run specific configuration."""
        issues = []
        warnings = []

        # Check for GCS profile sync configuration
        if not config.PW_PROFILE_GCS_BUCKET:
            warnings.append("PW_PROFILE_GCS_BUCKET not set - profile sync disabled")

        # Check if profile exists (local or will be synced)
        if not config.PW_USER_DATA_DIR.exists():
            if config.PW_PROFILE_GCS_BUCKET:
                warnings.append("Profile directory doesn't exist yet (will be synced from GCS on startup)")
            else:
                issues.append("Profile directory doesn't exist and GCS sync not configured")

        # Check credentials method
        if config.SA_JSON:
            warnings.append("Using SA_JSON (inline credentials)")
        elif config.GOOGLE_APPLICATION_CREDENTIALS:
            warnings.append(f"Using service account file: {config.GOOGLE_APPLICATION_CREDENTIALS}")
        else:
            warnings.append("Using Application Default Credentials (ADC)")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    @staticmethod
    def validate_all() -> dict:
        """Validate all configuration."""
        scraping = ConfigValidator.validate_scraping()
        google = ConfigValidator.validate_google()
        cloud_run = ConfigValidator.validate_cloud_run()

        return {
            "scraping": scraping,
            "google": google,
            "cloud_run": cloud_run,
            "all_valid": scraping["valid"] and google["valid"] and cloud_run["valid"],
        }


def validate_mycase_session() -> dict:
    """
    Perform a live check of the MyCase session.
    Prioritizes state-based (cookies) session if available.
    """
    from src.core.context_manager import mycase_session_state, load_state_path
    
    # Check if we have a state (cookies) available
    state_path = load_state_path()
    
    try:
        logger.info("Performing consolidated session validation...")
        with mycase_auto_session() as page:
            is_active = check_session_active(page)
            
            user_info = None
            if is_active:
                try:
                    user_el = page.query_selector(".user-name, .profile-name, #user-menu")
                    if user_el:
                        user_info = user_el.inner_text().strip()
                except:
                    pass
            
            return {
                "session_active": is_active,
                "method": "state_cookies" if load_state_path() else "persistent_profile",
                "current_url": page.url,
                "user_info": user_info,
                "error": None if is_active else "Session invalid or expired"
            }
    except Exception as e:
        logger.error("Session validation failed: %s", e)
        return {
            "session_active": False,
            "method": "state_cookies" if load_state_path() else "persistent_profile",
            "current_url": None,
            "user_info": None,
            "error": str(e)
        }
