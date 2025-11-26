# core/config.py
"""
Consolidated configuration for the MyCase scraper project.
All settings are loaded from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================
# MYCASE AUTHENTICATION
# ============================================
MYCASE_EMAIL = os.getenv("MYCASE_EMAIL", "")
MYCASE_PASSWORD = os.getenv("MYCASE_PASSWORD", "")
MYCASE_BASE_URL = "https://the-mendoza-law-firm.mycase.com"
LOGIN_URL = "https://auth.mycase.com/login_sessions/new?response_type=code&client_id=tCEM8hNY7GaC2c8P&redirect_uri=https%3A%2F%2Fthe-mendoza-law-firm.mycase.com%2Fuser_sessions%2Fo_auth_callback&login_required=true"
DASHBOARD_URL = f"{MYCASE_BASE_URL}/dashboard"
BASE_CASE_URL = f"{MYCASE_BASE_URL}/court_cases"
BASE_LEADS_URL = f"{MYCASE_BASE_URL}/leads"

# ============================================
# LOCAL FILE STORAGE
# ============================================
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", r"C:\MyCaseDownloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# PLAYWRIGHT SETTINGS
# ============================================
# Directory for persistent browser profile (cookies, local storage)
PW_USER_DATA_DIR = Path(os.getenv("PW_USER_DATA_DIR", r"C:\ChromeProfiles\mycase_pw"))
PW_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Headless mode (True = no visible browser window)
PW_HEADLESS = os.getenv("PW_HEADLESS", "true").lower() == "true"

# Global timeout in milliseconds
PW_TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "8000"))

# Resource types to block for better performance
PW_BLOCK_RESOURCES = os.getenv(
    "PW_BLOCK_RESOURCES",
    "image,media,font,stylesheet"
).split(",")

# Browser channel to use (empty = default chromium, "chrome" = Google Chrome)
# For Cloud Run, leave empty to use installed chromium
PW_BROWSER_CHANNEL = os.getenv("PW_BROWSER_CHANNEL", "").strip()

# ============================================
# GOOGLE CLOUD CREDENTIALS
# ============================================
# Path to service account JSON file
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# Alternative: JSON content inline (for Cloud Run secrets)
SA_JSON = os.getenv("SA_JSON", "")

# ============================================
# GOOGLE SHEETS
# ============================================
SHEET_DEFAULT_ID = os.getenv("SHEET_DEFAULT_ID", "")
SHEET_DEFAULT_NAME = os.getenv("SHEET_DEFAULT_NAME", "Tasks")
SHEETS_VALUE_INPUT_OPTION = os.getenv("SHEETS_VALUE_INPUT_OPTION", "USER_ENTERED")

# ============================================
# GOOGLE DRIVE
# ============================================
DRIVE_DEFAULT_FOLDER_ID = os.getenv("DRIVE_DEFAULT_FOLDER_ID", "").strip()
DRIVE_USE_SHARED_DRIVE = os.getenv("DRIVE_USE_SHARED_DRIVE", "true").lower() == "true"

# ============================================
# GOOGLE CLOUD STORAGE
# ============================================
GCS_ARTIFACTS_BUCKET = os.getenv("GCS_ARTIFACTS_BUCKET", "").strip()
GCS_SIGNED_URL_TTL = int(os.getenv("GCS_SIGNED_URL_TTL", "604800"))  # 7 days in seconds

# ============================================
# CLOUD RUN SESSION PERSISTENCE
# ============================================
# GCS path for storing Playwright profile (for Cloud Run)
PW_PROFILE_GCS_BUCKET = os.getenv("PW_PROFILE_GCS_BUCKET", "").strip()
PW_PROFILE_GCS_PREFIX = os.getenv("PW_PROFILE_GCS_PREFIX", "playwright-profiles/mycase/")

# ============================================
# LOGGING
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = Path(os.getenv("LOG_FILE", "./logs/scraping.log"))
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ============================================
# API SETTINGS
# ============================================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true"
