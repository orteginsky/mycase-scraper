# core/exceptions.py
"""
Custom exceptions for the MyCase scraper project.
Provides clear error types for different failure scenarios.
"""


class MyCaseScraperError(Exception):
    """Base exception for all MyCase scraper errors."""
    pass


# ============================================
# AUTHENTICATION ERRORS
# ============================================
class AuthenticationError(MyCaseScraperError):
    """Failed to authenticate with MyCase."""
    pass


class SessionExpiredError(AuthenticationError):
    """Browser session has expired and needs re-login."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Username or password is incorrect."""
    pass


# ============================================
# SCRAPING ERRORS
# ============================================
class ScrapingError(MyCaseScraperError):
    """Generic error during scraping operation."""
    pass


class CaseNotFoundError(ScrapingError):
    """The requested case ID does not exist or is inaccessible."""
    def __init__(self, case_id: int, message: str = None):
        self.case_id = case_id
        super().__init__(message or f"Case {case_id} not found or inaccessible")


class DocumentDownloadError(ScrapingError):
    """Failed to download a document from MyCase."""
    pass


class PageTimeoutError(ScrapingError):
    """Page load or element wait timed out."""
    pass


class ElementNotFoundError(ScrapingError):
    """Expected DOM element was not found on page."""
    pass


class MessageSendError(ScrapingError):
    """Failed to send a message through MyCase."""
    pass


# ============================================
# STORAGE ERRORS
# ============================================
class StorageError(MyCaseScraperError):
    """Error with file storage operations."""
    pass


class DriveUploadError(StorageError):
    """Failed to upload file to Google Drive."""
    pass


class GCSUploadError(StorageError):
    """Failed to upload file to Google Cloud Storage."""
    pass


class LocalStorageError(StorageError):
    """Failed to save file locally."""
    pass


# ============================================
# INTEGRATION ERRORS
# ============================================
class GoogleSheetsError(MyCaseScraperError):
    """Error communicating with Google Sheets."""
    pass


class StatusUpdateError(GoogleSheetsError):
    """Failed to update task status in Google Sheets."""
    pass


# ============================================
# CONFIGURATION ERRORS
# ============================================
class ConfigurationError(MyCaseScraperError):
    """Missing or invalid configuration."""
    pass


class MissingCredentialsError(ConfigurationError):
    """Required credentials are not configured."""
    pass


class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid."""
    pass
