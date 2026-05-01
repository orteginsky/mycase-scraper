# core/credentials.py
"""
Centralized Google Cloud credentials management.
All clients should use these functions instead of duplicating credential logic.
"""
import json
from typing import List
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials

from src.core import config


def get_google_credentials(scopes: List[str]) -> Credentials:
    """
    Get Google service account credentials with specified scopes.

    Checks in order:
    1. SA_JSON environment variable (JSON content inline)
    2. GOOGLE_APPLICATION_CREDENTIALS file path

    Args:
        scopes: List of OAuth scopes required (e.g., ["https://www.googleapis.com/auth/drive.file"])

    Returns:
        Service account credentials

    Raises:
        RuntimeError: If no credentials are configured
    """
    # Option 1: JSON content inline (preferred for Cloud Run secrets)
    if config.SA_JSON:
        info = json.loads(config.SA_JSON)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)

    # Option 2: File path
    if config.GOOGLE_APPLICATION_CREDENTIALS:
        return service_account.Credentials.from_service_account_file(
            config.GOOGLE_APPLICATION_CREDENTIALS, scopes=scopes
        )

    raise RuntimeError(
        "No Google credentials configured. "
        "Set GOOGLE_APPLICATION_CREDENTIALS (file path) or SA_JSON (JSON content) in environment."
    )


# Pre-defined scope sets for convenience
SCOPES_DRIVE = ["https://www.googleapis.com/auth/drive.file"]
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_GCS = ["https://www.googleapis.com/auth/devstorage.read_write"]
SCOPES_DOCS = ["https://www.googleapis.com/auth/documents"]

# Combined scopes for apps that need multiple services
SCOPES_ALL = list(set(SCOPES_DRIVE + SCOPES_SHEETS + SCOPES_GCS + SCOPES_DOCS))


def get_drive_credentials() -> Credentials:
    """Get credentials for Google Drive API."""
    return get_google_credentials(SCOPES_DRIVE)


def get_sheets_credentials() -> Credentials:
    """Get credentials for Google Sheets API."""
    return get_google_credentials(SCOPES_SHEETS)


def get_gcs_credentials() -> Credentials:
    """Get credentials for Google Cloud Storage."""
    return get_google_credentials(SCOPES_GCS)


def get_docs_credentials() -> Credentials:
    """Get credentials for Google Docs API."""
    return get_google_credentials(SCOPES_DOCS)
