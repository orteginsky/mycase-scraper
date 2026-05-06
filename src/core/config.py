# core/config.py
"""
Consolidated configuration for the MyCase scraper project.
All settings are loaded from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# # ============================================
# PROJECT PATHS & ENVIRONMENT
# ============================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
IS_PROD = os.getenv("K_SERVICE") is not None  # K_SERVICE is standard in Cloud Run

def get_env_path(name: str, default: str) -> Path:
    """Gets a path from env, but ignores prod-specific paths if running locally."""
    val = os.getenv(name)
    if val and not IS_PROD and (val.startswith("/app") or val.startswith("/tmp")):
        # If we are local but the env says /app or /tmp, it's likely a config leak from prod.
        # We override it with the local default.
        return Path(default)
    return Path(val or default)

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
# In Cloud Run, /tmp is the only writable directory
DEFAULT_DOWNLOAD_DIR = "/tmp/downloads" if IS_PROD else str(BASE_DIR / "downloads")
DOWNLOAD_DIR = get_env_path("DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# SESSION STATE (cookie-based auth)
# ============================================
# Base64-encoded state.json content (for Docker/Cloud Run)
PW_STATE_B64 = os.getenv("PW_STATE_B64", "").strip()
# Local path to state.json file
STATE_FILE = Path(os.getenv("STATE_FILE", str(BASE_DIR / "state.json")))
# GCS remote path for state.json
STATE_REMOTE = os.getenv("STATE_REMOTE", "sessions/state.json")

# ============================================
# PLAYWRIGHT SETTINGS
# ============================================
# Directory for persistent browser profile (cookies, local storage)
DEFAULT_PW_DIR = "/tmp/playwright_data" if IS_PROD else str(BASE_DIR / ".playwright_data")
PW_USER_DATA_DIR = get_env_path("PW_USER_DATA_DIR", DEFAULT_PW_DIR)
PW_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Headless mode (True = no visible browser window)
PW_HEADLESS = os.getenv("PW_HEADLESS", "true").lower() == "true"

# Global timeout in milliseconds (30s is safer for Cloud Run)
PW_TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))

# Resource types to block for better performance
PW_BLOCK_RESOURCES = os.getenv(
    "PW_BLOCK_RESOURCES",
    "image,media,font,stylesheet"
).split(",")

# Browser channel to use (empty = default chromium, "chrome" = Google Chrome)
# For Cloud Run, leave empty to use installed chromium
PW_BROWSER_CHANNEL = os.getenv("PW_BROWSER_CHANNEL", "").strip()

# ============================================
# GCP SETTINGS
# ============================================
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
VERTEX_MODEL_ID = os.getenv("VERTEX_MODEL_ID", "gemini-1.5-pro")

# ============================================
# GOOGLE CLOUD CREDENTIALS
# ============================================
# Path to service account JSON file
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# Alternative: JSON content inline (for Cloud Run secrets)
# Also accepts GOOGLE_SERVICE_ACCOUNT for compatibility with MendozaFirm_IA scripts
SA_JSON = os.getenv("SA_JSON", "") or os.getenv("GOOGLE_SERVICE_ACCOUNT", "")

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
# CASE STAGE UPDATER (DAILY PWI)
# ============================================
CASE_STAGE_SPREADSHEET_ID = os.getenv(
    "CASE_STAGE_SPREADSHEET_ID",
    "1skEqWwYFXkhCpm_EIr_ht3mm07m2gvxrMBByqo115_w",
)
CASE_STAGE_SHEETS = os.getenv(
    "CASE_STAGE_SHEETS",
    "DAILY VAWA,DAILY VISA T,DAILY OTHER VISAS,DAILY NON VAWA",
).split(",")

# ============================================
# LOGGING
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEFAULT_LOG_FILE = "/tmp/scraping.log" if IS_PROD else str(BASE_DIR / "logs" / "scraping.log")
LOG_FILE = get_env_path("LOG_FILE", DEFAULT_LOG_FILE)

# Create log directory if not using /tmp
if not IS_PROD:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ============================================
# API SETTINGS
# ============================================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true"

if __name__ == "__main__":
    if IS_PROD:
        print("Entorno: PRODUCCIÓN (Cloud Run)")
    else:
        print(f"Entorno: LOCAL (Base: {BASE_DIR})")
    print(f"PW_USER_DATA_DIR: {PW_USER_DATA_DIR}")
    print(f"DOWNLOAD_DIR: {DOWNLOAD_DIR}")