# Google Apps Script Integration Guide

This guide shows how to integrate your Google Sheets with the MyCase Scraper API using Apps Script.

## Table of Contents
- [Google Sheet Structure](#google-sheet-structure)
- [Apps Script Setup](#apps-script-setup)
- [Trigger Configuration](#trigger-configuration)
- [Example Functions](#example-functions)
- [Error Handling](#error-handling)

---

## Google Sheet Structure

### Recommended Columns

| Column | Letter | Description | Example |
|--------|--------|-------------|---------|
| case_id | A | MyCase case/lead ID | 12345 |
| client_name | B | Client name | John Doe |
| action | C | Task type | download_pdfs |
| status | D | Current status | PENDING |
| result_url | E | Output URL | https://drive.google.com/... |
| completed_at | F | Timestamp | 2024-01-15T10:30:00Z |
| error_details | G | Error info (if failed) | TimeoutError |
| kind | H | lead or case | lead |

### Status Values

- **PENDING**: Task waiting to be processed
- **RUNNING**: Currently being processed
- **SUCCEEDED**: Completed successfully
- **FAILED: {error}**: Failed with error type

### Action Types

- `download_pdfs` - Download PDF documents
- `extract_notes` - Extract case notes
- `send_message` - Send text message

---

## Apps Script Setup

### 1. Open Script Editor

In your Google Sheet: **Extensions** → **Apps Script**

### 2. Configure API Base URL

```javascript
// Configuration
const CONFIG = {
  API_BASE: "https://your-cloud-run-service.run.app",
  SHEET_NAME: "Tasks",
  TIMEOUT_MS: 300000, // 5 minutes for long operations

  // Column indices (1-based)
  COL_CASE_ID: 1,
  COL_CLIENT_NAME: 2,
  COL_ACTION: 3,
  COL_STATUS: 4,
  COL_RESULT_URL: 5,
  COL_COMPLETED_AT: 6,
  COL_ERROR_DETAILS: 7,
  COL_KIND: 8,
};
```

---

## Example Functions

### Main Task Processor

```javascript
/**
 * Process a single task row from the sheet.
 * Called when status changes to "PENDING".
 */
function processTask(sheet, row) {
  const caseId = sheet.getRange(row, CONFIG.COL_CASE_ID).getValue();
  const clientName = sheet.getRange(row, CONFIG.COL_CLIENT_NAME).getValue();
  const action = sheet.getRange(row, CONFIG.COL_ACTION).getValue();
  const kind = sheet.getRange(row, CONFIG.COL_KIND).getValue() || "lead";

  // Validate required fields
  if (!caseId || !clientName || !action) {
    sheet.getRange(row, CONFIG.COL_STATUS).setValue("FAILED: Missing required fields");
    return;
  }

  // Route to appropriate endpoint
  let endpoint, payload;

  switch (action) {
    case "download_pdfs":
      endpoint = "/pdfs/download";
      payload = {
        case_id: parseInt(caseId),
        client_name: clientName,
        kind: kind,
        sheet_id: SpreadsheetApp.getActiveSpreadsheet().getId(),
        row: row,
        col: CONFIG.COL_STATUS,
        drive_folder_id: getDriveFolderId(), // Your function to get folder ID
      };
      break;

    case "extract_notes":
      endpoint = "/notes/extract";
      payload = {
        case_id: parseInt(caseId),
        client_name: clientName,
        kind: kind,
        output_format: "markdown",
        sheet_id: SpreadsheetApp.getActiveSpreadsheet().getId(),
        row: row,
        col: CONFIG.COL_STATUS,
      };
      break;

    case "send_message":
      const message = sheet.getRange(row, 9).getValue(); // Message in column I
      endpoint = "/messages/send";
      payload = {
        case_id: parseInt(caseId),
        message: message,
        client_name: clientName,
        sheet_id: SpreadsheetApp.getActiveSpreadsheet().getId(),
        row: row,
        col: CONFIG.COL_STATUS,
      };
      break;

    default:
      sheet.getRange(row, CONFIG.COL_STATUS).setValue("FAILED: Unknown action");
      return;
  }

  // Make API request
  callScraperAPI(endpoint, payload, sheet, row);
}

/**
 * Call the Scraper API endpoint.
 */
function callScraperAPI(endpoint, payload, sheet, row) {
  const url = CONFIG.API_BASE + endpoint;

  const options = {
    method: "POST",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
    timeout: CONFIG.TIMEOUT_MS,
  };

  try {
    const response = UrlFetchApp.fetch(url, options);
    const statusCode = response.getResponseCode();
    const responseData = JSON.parse(response.getContentText());

    if (statusCode === 200 && responseData.ok) {
      // Success - write result URL if available
      if (responseData.drive_folder_url) {
        sheet.getRange(row, CONFIG.COL_RESULT_URL).setValue(responseData.drive_folder_url);
      } else if (responseData.gdoc_url) {
        sheet.getRange(row, CONFIG.COL_RESULT_URL).setValue(responseData.gdoc_url);
      }

      // Update timestamp
      sheet.getRange(row, CONFIG.COL_COMPLETED_AT).setValue(new Date().toISOString());

    } else {
      // API returned error
      const errorMsg = responseData.error || responseData.detail || "Unknown error";
      sheet.getRange(row, CONFIG.COL_ERROR_DETAILS).setValue(errorMsg);
    }

  } catch (error) {
    // Network or script error
    sheet.getRange(row, CONFIG.COL_STATUS).setValue("FAILED: NetworkError");
    sheet.getRange(row, CONFIG.COL_ERROR_DETAILS).setValue(error.toString());
  }
}
```

### Trigger: onEdit

```javascript
/**
 * Trigger: Automatically process tasks when status is set to "PENDING".
 * Add this as an installable trigger.
 */
function onEditTrigger(e) {
  const sheet = e.source.getActiveSheet();

  // Only process the Tasks sheet
  if (sheet.getName() !== CONFIG.SHEET_NAME) return;

  const row = e.range.getRow();
  const col = e.range.getColumn();

  // Skip header row
  if (row === 1) return;

  // Check if status column was edited to "PENDING"
  if (col === CONFIG.COL_STATUS && e.value === "PENDING") {
    processTask(sheet, row);
  }
}
```

### Trigger: Time-Driven Batch Processing

```javascript
/**
 * Process all PENDING tasks in the sheet.
 * Use with time-driven trigger (e.g., every 5 minutes).
 */
function processPendingTasks() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();

  for (let row = 2; row <= lastRow; row++) {
    const status = sheet.getRange(row, CONFIG.COL_STATUS).getValue();

    if (status === "PENDING") {
      processTask(sheet, row);
      // Small delay between requests to avoid rate limiting
      Utilities.sleep(2000);
    }
  }
}
```

### Utility Functions

```javascript
/**
 * Get the Drive folder ID from a settings cell or property.
 */
function getDriveFolderId() {
  // Option 1: From a specific cell
  // return SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Settings").getRange("B2").getValue();

  // Option 2: From script properties
  // return PropertiesService.getScriptProperties().getProperty("DRIVE_FOLDER_ID");

  // Option 3: Hardcoded (not recommended for production)
  return "your-drive-folder-id-here";
}

/**
 * Add a new task to the queue.
 */
function addTask(caseId, clientName, action, kind = "lead") {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const newRow = sheet.getLastRow() + 1;

  sheet.getRange(newRow, CONFIG.COL_CASE_ID).setValue(caseId);
  sheet.getRange(newRow, CONFIG.COL_CLIENT_NAME).setValue(clientName);
  sheet.getRange(newRow, CONFIG.COL_ACTION).setValue(action);
  sheet.getRange(newRow, CONFIG.COL_STATUS).setValue("PENDING");
  sheet.getRange(newRow, CONFIG.COL_KIND).setValue(kind);
}

/**
 * Retry failed tasks.
 */
function retryFailedTasks() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
  const lastRow = sheet.getLastRow();

  for (let row = 2; row <= lastRow; row++) {
    const status = sheet.getRange(row, CONFIG.COL_STATUS).getValue();

    if (status.startsWith("FAILED:")) {
      // Reset to PENDING to retry
      sheet.getRange(row, CONFIG.COL_STATUS).setValue("PENDING");
      sheet.getRange(row, CONFIG.COL_ERROR_DETAILS).setValue("");
    }
  }
}

/**
 * Create a custom menu in the spreadsheet.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("MyCase Scraper")
    .addItem("Process Pending Tasks", "processPendingTasks")
    .addItem("Retry Failed Tasks", "retryFailedTasks")
    .addSeparator()
    .addItem("Check API Health", "checkAPIHealth")
    .addToUi();
}

/**
 * Check if the API is healthy.
 */
function checkAPIHealth() {
  const url = CONFIG.API_BASE + "/health";

  try {
    const response = UrlFetchApp.fetch(url);
    const data = JSON.parse(response.getContentText());

    SpreadsheetApp.getUi().alert(
      "API Health Check",
      `Status: ${data.status}\n` +
      `Playwright Profile: ${data.playwright_profile_exists}\n` +
      `Google Credentials: ${data.google_credentials_configured}`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  } catch (error) {
    SpreadsheetApp.getUi().alert("API Health Check Failed", error.toString(), SpreadsheetApp.getUi().ButtonSet.OK);
  }
}
```

---

## Trigger Configuration

### Install Triggers

1. In Apps Script editor, go to **Triggers** (clock icon)
2. Click **+ Add Trigger**

**For onEdit trigger:**
- Function: `onEditTrigger`
- Event source: From spreadsheet
- Event type: On edit

**For batch processing:**
- Function: `processPendingTasks`
- Event source: Time-driven
- Type: Every 5 minutes (or as needed)

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| NetworkError | API unreachable | Check Cloud Run service is running |
| AuthError | Invalid credentials | Verify MYCASE_EMAIL/PASSWORD in Cloud Run |
| NotFound | Case ID doesn't exist | Verify case_id is correct |
| TimeoutError | Operation took too long | Increase timeout or check for slow network |

### Logging

```javascript
/**
 * Log API call for debugging.
 */
function logAPICall(endpoint, payload, response) {
  console.log("API Call:", {
    endpoint: endpoint,
    payload: payload,
    status: response.getResponseCode(),
    body: response.getContentText(),
  });
}
```

---

## Payload Examples

### Download PDFs

```json
{
  "case_id": 12345,
  "client_name": "John Doe",
  "kind": "lead",
  "sheet_id": "1Dyq4QJgwKcW3LEAetga43CkAdvzBZDtW7vLddPugVfo",
  "row": 5,
  "col": 4,
  "drive_folder_id": "your-folder-id"
}
```

### Extract Notes

```json
{
  "case_id": 12345,
  "client_name": "John Doe",
  "kind": "case",
  "output_format": "markdown",
  "sheet_id": "1Dyq4QJgwKcW3LEAetga43CkAdvzBZDtW7vLddPugVfo",
  "row": 6,
  "col": 4
}
```

### Send Message

```json
{
  "case_id": 12345,
  "message": "Hello! This is an update about your case.",
  "client_name": "John Doe",
  "sheet_id": "1Dyq4QJgwKcW3LEAetga43CkAdvzBZDtW7vLddPugVfo",
  "row": 7,
  "col": 4,
  "verify_sent": true
}
```

---

## Security Considerations

1. **API Authentication**: Consider adding API keys or OAuth for production
2. **Rate Limiting**: Add delays between requests to avoid overwhelming the service
3. **Validation**: Always validate inputs before sending to API
4. **Secrets**: Store sensitive values in Script Properties, not in code
5. **Logging**: Monitor logs for suspicious activity

---

## Next Steps

1. Deploy your FastAPI service to Cloud Run
2. Update `CONFIG.API_BASE` with your Cloud Run URL
3. Set up Google Sheet with recommended columns
4. Install Apps Script triggers
5. Test with a single task before batch processing
