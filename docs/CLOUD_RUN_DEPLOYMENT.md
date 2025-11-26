# Cloud Run Deployment Guide

This guide walks you through deploying the MyCase scraper to Google Cloud Run with persistent session management.

## Overview

The main challenge with Cloud Run is maintaining authentication sessions since containers are stateless. This solution uses:

1. **GCS Profile Sync**: Stores authenticated Playwright browser profile in Google Cloud Storage
2. **Startup Download**: Container downloads profile on startup
3. **Session Persistence**: Cookies and local storage maintain MyCase login

## Prerequisites

- Google Cloud Project with billing enabled
- Cloud Run API enabled
- Cloud Storage bucket created
- Local authenticated Playwright profile (from running the scraper locally)
- Service account with appropriate permissions

## Step 1: Create Authenticated Profile Locally

First, create an authenticated Playwright profile on your local machine:

```bash
# Seed the profile with MyCase authentication
python scripts/seed_playwright_profile.py
```

This will:
- Open a browser window
- Navigate to MyCase login
- Wait for you to log in (including 2FA)
- Save the session to your local profile directory

The default profile location is `C:\ChromeProfiles\mycase_pw` (Windows) or configured via `PW_USER_DATA_DIR`.

## Step 2: Upload Profile to GCS

Upload your authenticated profile to Google Cloud Storage:

```bash
# Make sure these environment variables are set in .env:
# PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114
# GOOGLE_APPLICATION_CREDENTIALS=path/to/sa_key.json

python scripts/upload_profile_to_gcs.py
```

This will:
- Package your profile (excluding cache files)
- Upload to `gs://mycase-sessions-ortega-473114/playwright-profiles/mycase/profile.tar.gz`

## Step 3: Configure Service Account Permissions

Your Cloud Run service needs permission to read from the GCS bucket:

```bash
# Get the service account email used by Cloud Run
SA_EMAIL="$(gcloud run services describe mycase-scraper-api \
  --region us-central1 \
  --format='value(spec.template.spec.serviceAccount)')"

# If empty, it's using the default compute service account
if [ -z "$SA_EMAIL" ]; then
  PROJECT_ID="$(gcloud config get-value project)"
  SA_EMAIL="${PROJECT_ID}-compute@developer.gserviceaccount.com"
  echo "Using default compute service account: $SA_EMAIL"
fi

# Grant storage permissions
gcloud storage buckets add-iam-policy-binding gs://mycase-sessions-ortega-473114 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"

# Also grant admin role if you want to upload profiles from Cloud Run
gcloud storage buckets add-iam-policy-binding gs://mycase-sessions-ortega-473114 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"
```

## Step 4: Set Environment Variables

Configure Cloud Run with required environment variables:

```bash
gcloud run services update mycase-scraper-api \
  --region us-central1 \
  --set-env-vars="\
MYCASE_EMAIL=your-email@example.com,\
MYCASE_PASSWORD=your-password,\
PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114,\
PW_PROFILE_GCS_PREFIX=playwright-profiles/mycase/,\
PW_HEADLESS=true,\
GOOGLE_APPLICATION_CREDENTIALS=/app/sa_key.json"
```

### Required Environment Variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `MYCASE_EMAIL` | MyCase login email | `user@example.com` |
| `MYCASE_PASSWORD` | MyCase login password | `your-password` |
| `PW_PROFILE_GCS_BUCKET` | GCS bucket for profile storage | `mycase-sessions-ortega-473114` |
| `PW_PROFILE_GCS_PREFIX` | Path prefix in bucket | `playwright-profiles/mycase/` |
| `PW_HEADLESS` | Run browser in headless mode | `true` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | `/app/sa_key.json` |

### Optional Environment Variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DRIVE_DEFAULT_FOLDER_ID` | Default Google Drive folder for uploads | (empty) |
| `SHEET_DEFAULT_ID` | Default Google Sheets ID for status updates | (empty) |
| `PW_TIMEOUT_MS` | Playwright timeout in milliseconds | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Step 5: Deploy to Cloud Run

Build and deploy your container:

```bash
# Build the container
gcloud builds submit --tag gcr.io/ortega-473114/mycase-scraper-api

# Deploy to Cloud Run
gcloud run deploy mycase-scraper-api \
  --image gcr.io/ortega-473114/mycase-scraper-api \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 10 \
  --set-env-vars="MYCASE_EMAIL=your-email@example.com,MYCASE_PASSWORD=your-password,PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114"
```

## Step 6: Verify Deployment

Check that the profile sync is working:

```bash
# View logs
gcloud run services logs read mycase-scraper-api --region us-central1 --limit 50

# Look for these success messages:
# "Profile Sync Configuration:"
# "✅ Playwright profile synced from GCS successfully"
# "Cookies file exists: True"
```

Test the API:

```bash
# Health check
curl https://mycase-scraper-api-223080314602.us-central1.run.app/health

# Detailed config validation
curl https://mycase-scraper-api-223080314602.us-central1.run.app/config/validate

# Send a test message
curl -X POST https://mycase-scraper-api-223080314602.us-central1.run.app/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": 12345,
    "client_name": "Test Client",
    "message": "Test message from Cloud Run"
  }'
```

## Troubleshooting

### Issue: "Invalid service account ()"

**Cause**: Cloud Run doesn't have a service account configured.

**Solution**: Explicitly set a service account:
```bash
gcloud run services update mycase-scraper-api \
  --region us-central1 \
  --service-account YOUR-SERVICE-ACCOUNT@ortega-473114.iam.gserviceaccount.com
```

### Issue: 401 Unauthorized / Authentication Failed

**Cause**: Profile doesn't have valid cookies or wasn't uploaded correctly.

**Solutions**:
1. Verify profile was uploaded:
   ```bash
   gcloud storage ls gs://mycase-sessions-ortega-473114/playwright-profiles/mycase/
   ```

2. Check logs for profile sync errors:
   ```bash
   gcloud run services logs read mycase-scraper-api --region us-central1 --limit 100
   ```

3. Re-create and upload profile:
   ```bash
   python scripts/seed_playwright_profile.py
   python scripts/upload_profile_to_gcs.py
   ```

### Issue: Profile sync fails with permission error

**Cause**: Service account doesn't have access to GCS bucket.

**Solution**: Grant storage permissions (see Step 3)

### Issue: Container timeout

**Cause**: Default timeout (60s) is too short for scraping operations.

**Solution**: Increase timeout:
```bash
gcloud run services update mycase-scraper-api \
  --region us-central1 \
  --timeout 900
```

### Issue: Out of memory

**Cause**: Chromium requires significant memory.

**Solution**: Increase memory allocation:
```bash
gcloud run services update mycase-scraper-api \
  --region us-central1 \
  --memory 2Gi
```

## Profile Refresh Strategy

Sessions expire over time. You have two options:

### Option 1: Manual Refresh (Recommended)
Periodically re-authenticate locally and upload:
```bash
python scripts/seed_playwright_profile.py
python scripts/upload_profile_to_gcs.py
```

### Option 2: Automatic Upload After Success
Uncomment profile sync in the message sending endpoint to upload after each successful operation.

## Monitoring

Monitor your deployment:

```bash
# Real-time logs
gcloud run services logs tail mycase-scraper-api --region us-central1

# Check service status
gcloud run services describe mycase-scraper-api --region us-central1

# View metrics in Cloud Console
https://console.cloud.google.com/run/detail/us-central1/mycase-scraper-api/metrics
```

## Security Best Practices

1. **Never commit credentials**: Use Cloud Secret Manager for sensitive data
2. **Rotate credentials**: Change MyCase password and update environment variables periodically
3. **Limit access**: Use Cloud Run authentication for production
4. **Monitor usage**: Set up alerts for unusual activity
5. **Encrypt at rest**: GCS buckets encrypt by default, but verify settings

## Cost Optimization

- Use **minimum instances: 0** to scale to zero when not in use
- Set **max instances** to prevent runaway costs
- Use **smaller memory** if possible (1Gi minimum for Chromium)
- Monitor **request counts** and optimize scraping logic

## Next Steps

1. Set up Cloud Scheduler to refresh profile periodically
2. Add monitoring and alerting
3. Implement retry logic for failed requests
4. Consider using Cloud Run Jobs for batch operations
