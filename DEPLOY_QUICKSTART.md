# Quick Deployment Guide

## Prerequisites Checklist
- [ ] Google Cloud project created (`ortega-473114`)
- [ ] Cloud Run API enabled
- [ ] GCS bucket created (`mycase-sessions-ortega-473114`)
- [ ] Service account key downloaded (`sa_key.json`)
- [ ] `.env` file configured with Windows paths for local development

## Step 1: Configure Local Environment

Edit `.env` file:
```bash
# Windows paths for local development
PW_USER_DATA_DIR=C:\ChromeProfiles\mycase_pw
DOWNLOAD_DIR=C:\MyCaseDownloads

# GCS bucket for profile sync
PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114
PW_PROFILE_GCS_PREFIX=playwright-profiles/mycase/

# Google credentials
GOOGLE_APPLICATION_CREDENTIALS=C:\Users\HoneyMaldonado\Documents\scraping\sa_key.json

# MyCase credentials
MYCASE_EMAIL=am.mendoza@mendozafirm.com
MYCASE_PASSWORD=your-password
```

## Step 2: Create Authenticated Profile

**IMPORTANT**: Follow instructions carefully - do NOT interrupt!

```powershell
python scripts/seed_playwright_profile.py
```

**Wait for:**
1. Browser to open
2. Log in to MyCase
3. Complete 2FA
4. See dashboard
5. Press ENTER (NOT Ctrl+C!)

**Expected output:**
```
✅ SUCCESS! Session saved successfully
   Cookies file: C:\ChromeProfiles\mycase_pw\Default\Cookies
```

## Step 3: Upload Profile to GCS

```powershell
python scripts/upload_profile_to_gcs.py
```

**Expected output:**
```
✅ Profile uploaded successfully!
```

## Step 4: Fix Service Account (Cloud Shell)

In Google Cloud Shell:

```bash
# Get service account
SA_EMAIL="$(gcloud run services describe mycase-scraper-api \
  --region us-central1 \
  --format='value(spec.template.spec.serviceAccount)')"

# If empty, use default
if [ -z "$SA_EMAIL" ]; then
  PROJECT_ID="$(gcloud config get-value project)"
  SA_EMAIL="${PROJECT_ID}-compute@developer.gserviceaccount.com"
fi

echo "Service Account: $SA_EMAIL"

# Grant permissions
gcloud storage buckets add-iam-policy-binding gs://mycase-sessions-ortega-473114 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"
```

## Step 5: Update Environment Variables (Cloud Shell)

```bash
gcloud run services update mycase-scraper-api \
  --region us-central1 \
  --set-env-vars="MYCASE_EMAIL=am.mendoza@mendozafirm.com,MYCASE_PASSWORD=Mendoza1998,PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114,PW_HEADLESS=true"
```

## Step 6: Verify Deployment

```bash
# Check logs
gcloud run services logs read mycase-scraper-api --region us-central1 --limit 50

# Look for:
# ✅ Playwright profile synced from GCS successfully
# Cookies file exists: True
```

## Step 7: Test API

```bash
# Get service URL
SERVICE_URL="$(gcloud run services describe mycase-scraper-api \
  --region us-central1 \
  --format='value(status.url)')"

# Health check
curl $SERVICE_URL/health

# Config validation
curl $SERVICE_URL/config/validate

# Test message send
curl -X POST $SERVICE_URL/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": 12345,
    "client_name": "Test Client",
    "message": "Test from Cloud Run"
  }'
```

## Troubleshooting

### Profile not syncing?
```bash
# Check if profile exists in GCS
gcloud storage ls gs://mycase-sessions-ortega-473114/playwright-profiles/mycase/
```

### Authentication failing?
Re-create and upload profile:
```powershell
python scripts/seed_playwright_profile.py
python scripts/upload_profile_to_gcs.py
```

### Permission errors?
Re-run Step 4 to grant service account permissions

### 401 Unauthorized?
Profile cookies expired - re-run Step 2 & 3

## Session Maintenance

Cookies expire over time. Refresh monthly:

```powershell
# Re-authenticate
python scripts/seed_playwright_profile.py

# Upload new profile
python scripts/upload_profile_to_gcs.py

# Force Cloud Run to reload
gcloud run services update mycase-scraper-api \
  --region us-central1 \
  --update-env-vars=PROFILE_VERSION=$(date +%s)
```

## Common Commands

```bash
# View real-time logs
gcloud run services logs tail mycase-scraper-api --region us-central1

# Check service status
gcloud run services describe mycase-scraper-api --region us-central1

# List all revisions
gcloud run revisions list --service mycase-scraper-api --region us-central1
```
