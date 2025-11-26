# MyCase Scraper API

REST API service for automating MyCase data extraction and integration with Google Cloud services.

## Features

- **PDF Download**: Extract documents from MyCase leads and cases
- **Notes Extraction**: Extract case notes and metadata
- **Message Sending**: Send text messages to clients through MyCase
- **Google Drive Integration**: Automatically upload files to Drive
- **Google Sheets Tracking**: Track task status in real-time
- **Cloud Run Ready**: Session persistence with GCS profile sync

## Architecture

```
scraping/
├── api/                    # FastAPI application
│   ├── app.py              # Main app entry point
│   ├── endpoints/          # API routers
│   │   ├── pdfs.py         # POST /pdfs/download
│   │   ├── notes.py        # POST /notes/extract
│   │   └── messages.py     # POST /messages/send
│   ├── schemas.py          # Pydantic models
│   └── status_writer.py    # Google Sheets integration
│
├── core/                   # Core infrastructure
│   ├── config.py           # Consolidated settings
│   ├── credentials.py      # Google auth management
│   ├── context_manager.py  # Playwright session management
│   ├── exceptions.py       # Custom exceptions
│   └── profile_sync.py     # GCS profile persistence
│
├── scraping/               # MyCase scraping logic
│   ├── documents.py        # PDF download
│   ├── notes.py            # Notes extraction
│   └── messaging.py        # Text message sending
│
├── clients/                # Google service clients
│   ├── drive_client.py     # Drive API
│   ├── sheets_client.py    # Sheets API
│   └── gcs_client.py       # Cloud Storage
│
├── utils/                  # Utilities
│   ├── logger.py           # Centralized logging
│   ├── text_utils.py       # Text sanitization
│   └── a1.py               # Column to A1 notation
│
└── docs/                   # Documentation
    └── APPS_SCRIPT_INTEGRATION.md
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

Create `.env` file:

```env
# MyCase credentials
MYCASE_EMAIL=your-email@firm.com
MYCASE_PASSWORD=your-password

# Playwright settings
PW_USER_DATA_DIR=C:\ChromeProfiles\mycase_pw
PW_HEADLESS=true
PW_TIMEOUT_MS=8000

# Google credentials
GOOGLE_APPLICATION_CREDENTIALS=./sa_key.json
# Or use inline JSON:
# SA_JSON={"type":"service_account",...}

# Google Sheets (optional)
SHEET_DEFAULT_ID=your-sheet-id
SHEET_DEFAULT_NAME=Tasks

# Google Drive (optional)
DRIVE_DEFAULT_FOLDER_ID=your-folder-id

# For Cloud Run (optional)
PW_PROFILE_GCS_BUCKET=your-bucket
PW_PROFILE_GCS_PREFIX=playwright-profiles/mycase/
```

### 3. Seed Playwright Profile (First Time)

```bash
python scripts/seed_playwright_profile.py
```

This opens a browser to manually log into MyCase and save session cookies.

### 4. Run the API

```bash
python -m api.app
# Or:
uvicorn api.app:app --host 0.0.0.0 --port 8080 --reload
```

### 5. Test Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Download PDFs
curl -X POST http://localhost:8080/pdfs/download \
  -H "Content-Type: application/json" \
  -d '{"case_id": 12345, "client_name": "John Doe", "kind": "lead"}'

# Extract notes
curl -X POST http://localhost:8080/notes/extract \
  -H "Content-Type: application/json" \
  -d '{"case_id": 12345, "client_name": "John Doe", "kind": "case"}'

# Send message
curl -X POST http://localhost:8080/messages/send \
  -H "Content-Type: application/json" \
  -d '{"case_id": 12345, "message": "Hello from API"}'
```

## API Endpoints

### Health & Status

- `GET /` - Basic health check
- `GET /health` - Detailed health status
- `GET /config/validate` - Configuration validation

### Core Operations

- `POST /pdfs/download` - Download PDFs from MyCase
- `POST /notes/extract` - Extract case notes
- `POST /messages/send` - Send text message

### Legacy (Backward Compatibility)

- `POST /download-pdfs` - Redirects to `/pdfs/download`

## Google Sheets Integration

The API can automatically update task status in Google Sheets:

1. Set up a Google Sheet with columns: case_id, client_name, action, status, result_url
2. Configure Apps Script to call the API (see `docs/APPS_SCRIPT_INTEGRATION.md`)
3. Include `sheet_id`, `row`, and `col` in request payloads

## Cloud Run Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg fonts-liberation libasound2 libatk-bridge2.0-0 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libxss1 \
    libxtst6 xdg-utils

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium

COPY . .

# Ensure directories exist
RUN mkdir -p /app/downloads /app/logs /app/playwright_profile

ENV PW_USER_DATA_DIR=/app/playwright_profile
ENV DOWNLOAD_DIR=/app/downloads
ENV PW_HEADLESS=true

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Session Persistence

For Cloud Run (stateless), use GCS to persist browser profile:

1. Set `PW_PROFILE_GCS_BUCKET` and `PW_PROFILE_GCS_PREFIX`
2. Profile is downloaded on startup and uploaded after successful login
3. First deployment: manually seed profile and upload to GCS

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_endpoints.py -v

# With coverage
pytest --cov=api tests/
```

## Logging

Logs are written to:
- Console (INFO level)
- File: `./logs/scraping.log` (DEBUG level)

Configure with `LOG_LEVEL` and `LOG_FILE` environment variables.

## Security Considerations

1. **Credentials**: Never commit `.env` or `sa_key.json` to git
2. **Rate Limiting**: Add delays between scraping operations
3. **API Authentication**: Consider adding API keys for production
4. **Error Handling**: Sensitive data is not exposed in error messages

## Migration from Old Scripts

If you have old standalone scripts (using CSV files):

1. Old workflow: CSV → Script reads rows → Process each
2. New workflow: Google Sheet → Apps Script detects changes → API processes

The API provides the same functionality with:
- Better error handling
- Status tracking
- Cloud deployment support
- Parallel processing capabilities

## Contributing

1. Follow existing code style (black formatter)
2. Add tests for new features
3. Update documentation
4. Use conventional commits

## License

Proprietary - Internal use only.
