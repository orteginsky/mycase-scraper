#!/usr/bin/env python3
"""
Seed Playwright profile with MyCase authentication.

This script:
1. Opens a browser with persistent profile
2. Navigates to MyCase login
3. Waits for you to manually log in (including 2FA)
4. Saves the session cookies/tokens for future use

Usage:
    python scripts/seed_playwright_profile.py

IMPORTANT:
- Do NOT close the browser manually
- Do NOT press Ctrl+C
- Wait for login to complete, then press ENTER
"""
from playwright.sync_api import sync_playwright
from time import sleep
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import config

# Use configured profile directory
USER_DATA_DIR = str(config.PW_USER_DATA_DIR)
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Use "chrome" for local seeding (better compatibility)
BROWSER_CHANNEL = "chrome"

print("=" * 70)
print("MyCase Profile Authentication Setup")
print("=" * 70)
print(f"\n📁 Profile Directory: {USER_DATA_DIR}")
print(f"🌐 Browser: {BROWSER_CHANNEL}")
print("\nIMPORTANT:")
print("  ⚠️  Do NOT close the browser manually")
print("  ⚠️  Do NOT press Ctrl+C")
print("  ✅  Press ENTER here AFTER you've logged in successfully")
print("=" * 70)
print()

try:
    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": USER_DATA_DIR,
            "headless": False,
            "args": [
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--password-store=basic",      # Ensure local credential storage
                "--use-mock-keychain",         # Avoid Windows user-specific encryption
            ],
        }

        if BROWSER_CHANNEL:
            launch_kwargs["channel"] = BROWSER_CHANNEL

        print("🚀 Launching browser...")
        context = p.chromium.launch_persistent_context(**launch_kwargs)

        page = context.new_page()
        print("🌐 Navigating to MyCase login...")
        page.goto("https://auth.mycase.com/login_sessions/new?login_required=true")

        print("\n" + "=" * 70)
        print("👉  Browser is now open")
        print("📋  Steps:")
        print("    1. Log in with your MyCase credentials")
        print("    2. Complete 2FA if prompted")
        print("    3. Check 'Remember this device' if available")
        print("    4. Wait until you see the MyCase dashboard")
        print("    5. Press ENTER in this terminal")
        print("=" * 70)
        print()

        input("🟢 Press ENTER when you're logged in and see the dashboard: ")

        print("\n💾 Saving session state...")
        print("   Waiting for cookies to be written...")
        sleep(3)

        # Verify we're logged in
        current_url = page.url
        if "dashboard" in current_url or "mycase.com" in current_url:
            print(f"✅ Current URL looks good: {current_url}")
        else:
            print(f"⚠️  Warning: Current URL doesn't look like MyCase: {current_url}")
            print("   Session may not be valid")

        print("   Closing browser...")
        context.close()

        # Check if cookies were saved (Chrome moved cookies to Network subfolder)
        cookies_paths = [
            Path(USER_DATA_DIR) / "Default" / "Network" / "Cookies",
            Path(USER_DATA_DIR) / "Default" / "Cookies",
        ]

        cookies_found = False
        for cookies_path in cookies_paths:
            if cookies_path.exists():
                print("\n✅ SUCCESS! Session saved successfully")
                print(f"   Cookies file: {cookies_path}")
                print(f"   Profile ready for upload to GCS")
                cookies_found = True
                break

        if not cookies_found:
            print("\n⚠️  WARNING: Cookies file not found")
            print("   The session may not have been saved properly")
            print("   You may need to run this script again")

except KeyboardInterrupt:
    print("\n\n❌ Script interrupted!")
    print("⚠️  Session was NOT saved properly")
    print("Please run the script again and press ENTER instead of Ctrl+C")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("Please try running the script again")
    sys.exit(1)

print("\n" + "=" * 70)
print("Next step: Upload profile to GCS")
print("Run: python scripts/upload_profile_to_gcs.py")
print("=" * 70)
