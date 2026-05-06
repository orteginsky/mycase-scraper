# api/schemas.py
"""
Pydantic models for API request/response validation.
Shared mixins for common fields (tracking, storage).
"""
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# BASE MIXINS
# ============================================
class SheetTrackingMixin(BaseModel):
    """Optional fields for tracking task status in Google Sheets."""
    sheet_id: Optional[str] = Field(
        None, description="Google Sheet ID for status tracking"
    )
    row: Optional[int] = Field(
        None, ge=1, description="Row number in the sheet (1-indexed)"
    )
    col: Optional[int] = Field(
        None, ge=1, description="Column number for status (1-indexed)"
    )


class StorageDestinationMixin(BaseModel):
    """Optional fields for cloud storage destinations."""
    drive_folder_id: Optional[str] = Field(
        None, description="Google Drive folder ID for uploads (uses default if not provided)"
    )


# ============================================
# DOWNLOAD PDFs ENDPOINT
# ============================================
class DownloadPDFRequest(SheetTrackingMixin, StorageDestinationMixin):
    """Request model for downloading PDFs from MyCase."""
    case_id: int = Field(..., description="ID of the lead or court case in MyCase")
    client_name: Optional[str] = Field(
        None, description="Client name (used for subfolder naming)"
    )
    kind: Literal["lead", "case"] = Field(
        "lead", description="Entity type: 'lead' or 'case'"
    )


class DriveFileInfo(BaseModel):
    """Information about a file uploaded to Google Drive."""
    id: str
    name: str
    webViewLink: Optional[str] = None


class DownloadPDFResponse(BaseModel):
    """Response model for PDF download operation."""
    ok: bool = Field(..., description="Whether the operation succeeded")
    kind: Literal["lead", "case"]
    case_id: int
    subfolder: str = Field(..., description="Local subfolder name")
    target_dir: str = Field(..., description="Full path to local directory")

    # Timing
    started_at: float = Field(..., description="Unix timestamp when task started")
    finished_at: float = Field(..., description="Unix timestamp when task finished")

    # Files info
    files_downloaded: int = Field(0, description="Number of files downloaded")
    total_files_found: int = Field(0, description="Total documents found on page")
    local_files: List[str] = Field(default_factory=list, description="Paths to downloaded files")

    # Error (if any)
    error: Optional[str] = None

    # Google Drive info (if uploaded)
    drive_parent_id: Optional[str] = None
    drive_target_folder_id: Optional[str] = None
    drive_files_count: Optional[int] = None
    drive_files: Optional[List[DriveFileInfo]] = None
    drive_folder_url: Optional[str] = None

    # GCS info (if uploaded)
    gcs_bucket: Optional[str] = None
    gcs_prefix: Optional[str] = None
    gcs_files_count: Optional[int] = None
    gcs_signed_urls: Optional[List[str]] = None


# ============================================
# EXTRACT NOTES ENDPOINT
# ============================================
class ExtractNotesRequest(SheetTrackingMixin, StorageDestinationMixin):
    """Request model for extracting notes from MyCase."""
    case_id: int = Field(..., description="ID of the lead or court case in MyCase")
    client_name: Optional[str] = Field(
        None, description="Client name (for reference)"
    )
    kind: Literal["lead", "case"] = Field(
        "case", description="Entity type: 'lead' or 'case'"
    )
    output_format: Literal["json", "markdown", "text"] = Field(
        "json", description="Format for notes output"
    )
    save_to_gdoc: bool = Field(
        False, description="If True, save notes to a Google Doc"
    )
    gdoc_id: Optional[str] = Field(
        None, description="Existing Google Doc ID to append notes to"
    )
    type: Optional[str] = Field(
        None, description="Informational parameter to be passed through"
    )


class NoteItem(BaseModel):
    """A single note entry from MyCase."""
    id: Optional[str] = None
    subject: Optional[str] = None
    body: str
    author: Optional[str] = None
    date: Optional[str] = None


class ExtractNotesResponse(BaseModel):
    """Response model for notes extraction operation."""
    ok: bool = Field(..., description="Whether the operation succeeded")
    case_id: int
    client_name: Optional[str] = None
    kind: Literal["lead", "case"]
    type: Optional[str] = None

    # Timing
    started_at: float
    finished_at: float

    # Case metadata
    case_name: Optional[str] = None
    date_opened: Optional[str] = None
    case_type: Optional[str] = None

    # Notes data
    notes_count: int = Field(0, description="Number of notes extracted")
    notes: List[NoteItem] = Field(default_factory=list)

    # Output
    output_format: str
    notes_text: Optional[str] = Field(
        None, description="Notes formatted as text/markdown (if requested)"
    )

    # Google Doc (if created/updated)
    gdoc_id: Optional[str] = None
    gdoc_url: Optional[str] = None

    # GCS (if saved)
    gcs_uri: Optional[str] = None
    gcs_signed_url: Optional[str] = None

    # Error (if any)
    error: Optional[str] = None


# ============================================
# SEND MESSAGE ENDPOINT
# ============================================
class SendMessageRequest(SheetTrackingMixin):
    """Request model for sending a text message through MyCase."""
    case_id: int = Field(..., description="Court case ID in MyCase")
    message: str = Field(
        ..., min_length=1, max_length=1600, description="Message text to send"
    )
    client_name: Optional[str] = Field(
        None, description="Client name (for logging/reference)"
    )
    verify_sent: bool = Field(
        False, description="If True, verify message appears in chat after sending"
    )


class SendMessageResponse(BaseModel):
    """Response model for message send operation."""
    ok: bool = Field(..., description="Whether the operation succeeded")
    case_id: int
    client_name: Optional[str] = None

    # Message info
    message_sent: str = Field(..., description="The message that was sent")
    sent_at: Optional[str] = Field(None, description="ISO timestamp when message was sent")
    verified: Optional[bool] = Field(
        None, description="Whether message was verified in chat (if requested)"
    )

    # Timing
    started_at: float
    finished_at: float

    # Error (if any)
    error: Optional[str] = None


# ============================================
# CASE NAME ENDPOINT
# ============================================
class CaseNameRequest(SheetTrackingMixin):
    """Request model for extracting a case name from MyCase."""
    case_id: int = Field(..., description="The unique numeric ID of the court case in MyCase")


class CaseNameResponse(BaseModel):
    """Response model for case name extraction operation."""
    ok: bool = Field(..., description="Whether the operation succeeded")
    case_id: int
    case_name: Optional[str] = None
    url: Optional[str] = None
    extracted_at: Optional[str] = None
    
    # Timing
    started_at: float
    finished_at: float
    
    # Error (if any)
    error: Optional[str] = None


# ============================================
# UPDATE CASE STAGES ENDPOINT
# ============================================
class UpdateCaseStagesRequest(BaseModel):
    """Request model for batch Case Stage update from Google Sheets."""
    spreadsheet_id: Optional[str] = Field(
        None, description="Spreadsheet ID (uses CASE_STAGE_SPREADSHEET_ID env var if omitted)"
    )
    sheets: Optional[List[str]] = Field(
        None, description="Sheet names to process (uses CASE_STAGE_SHEETS env var if omitted)"
    )


class SheetUpdateResult(BaseModel):
    """Per-sheet summary of Case Stage update results."""
    sheet_name: str
    ok: int = 0
    errors: int = 0
    skipped: int = 0


class UpdateCaseStagesResponse(BaseModel):
    """Response model for batch Case Stage update operation."""
    ok: bool = Field(..., description="Whether the batch completed without fatal errors")
    total_ok: int = 0
    total_errors: int = 0
    total_skipped: int = 0
    sheets: List[SheetUpdateResult] = Field(default_factory=list)

    started_at: float
    finished_at: float

    error: Optional[str] = None


# ============================================
# HEALTH CHECK
# ============================================
class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    version: str = "1.0.0"
    playwright_profile_exists: bool = False
    google_credentials_configured: bool = False
    session_active: Optional[bool] = None
    session_error: Optional[str] = None
    user_info: Optional[str] = None


# ============================================
# ERROR RESPONSE
# ============================================
class ErrorResponse(BaseModel):
    """Standard error response model."""
    ok: bool = False
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Exception type name")
    detail: Optional[Dict[str, Any]] = None
