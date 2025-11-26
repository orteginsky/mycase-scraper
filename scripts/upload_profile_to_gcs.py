#!/usr/bin/env python3
"""
Upload local Playwright profile to GCS for Cloud Run deployment.

Usage:
    python scripts/upload_profile_to_gcs.py

This script:
1. Creates an authenticated Playwright session locally
2. Packages the profile (excluding cache files)
3. Uploads to GCS bucket for Cloud Run to download on startup

Prerequisites:
- Run seed_playwright_profile.py first to create an authenticated profile
- Set GOOGLE_APPLICATION_CREDENTIALS or have ADC configured
- Set PW_PROFILE_GCS_BUCKET in .env
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import config
from core.profile_sync import upload_profile_to_gcs
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Upload Playwright profile to GCS."""
    logger.info("=" * 60)
    logger.info("Playwright Profile Upload to GCS")
    logger.info("=" * 60)

    # Validate configuration
    if not config.PW_PROFILE_GCS_BUCKET:
        logger.error("PW_PROFILE_GCS_BUCKET not configured in environment")
        logger.error("Add to .env: PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114")
        return 1

    if not config.PW_USER_DATA_DIR.exists():
        logger.error("Profile directory does not exist: %s", config.PW_USER_DATA_DIR)
        logger.error("Run scripts/seed_playwright_profile.py first to create an authenticated profile")
        return 1

    # Check if profile has content
    profile_files = list(config.PW_USER_DATA_DIR.rglob("*"))
    if not profile_files:
        logger.error("Profile directory is empty: %s", config.PW_USER_DATA_DIR)
        logger.error("Run scripts/seed_playwright_profile.py first to create an authenticated profile")
        return 1

    logger.info("Profile directory: %s", config.PW_USER_DATA_DIR)
    logger.info("Profile contains %d files/directories", len(profile_files))
    logger.info("GCS Bucket: %s", config.PW_PROFILE_GCS_BUCKET)
    logger.info("GCS Prefix: %s", config.PW_PROFILE_GCS_PREFIX)

    # Upload
    logger.info("")
    logger.info("Starting upload...")
    success = upload_profile_to_gcs()

    if success:
        logger.info("")
        logger.info("✅ Profile uploaded successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Deploy to Cloud Run with environment variables:")
        logger.info("   - PW_PROFILE_GCS_BUCKET=%s", config.PW_PROFILE_GCS_BUCKET)
        logger.info("   - MYCASE_EMAIL=<your-email>")
        logger.info("   - MYCASE_PASSWORD=<your-password>")
        logger.info("")
        logger.info("2. Ensure service account has storage.objectViewer role")
        logger.info("")
        return 0
    else:
        logger.error("")
        logger.error("❌ Failed to upload profile")
        logger.error("Check logs above for errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
