# api/endpoints/pdfs.py
"""
Endpoint for downloading PDFs from MyCase.
"""
import time
from fastapi import APIRouter, HTTPException

from src.api.schemas import DownloadPDFRequest, DownloadPDFResponse, DriveFileInfo
from src.api.status_writer import TaskStatusTracker
from src.core import mycase_auto_session
from src.core import config
from src.core.exceptions import CaseNotFoundError, DocumentDownloadError, AuthenticationError
from src.scraping.documents import download_pdfs
from src.clients.drive_client import upload_directory
from src.utils.text_utils import sanitize_folder_name
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pdfs", tags=["PDFs"])


@router.post("/download", response_model=DownloadPDFResponse)
def download_pdfs_endpoint(req: DownloadPDFRequest) -> DownloadPDFResponse:
    """
    Download PDF documents from a MyCase lead or case.

    This endpoint:
    1. Logs into MyCase (uses persistent session)
    2. Navigates to the documents section
    3. Downloads all PDFs to local storage
    4. Optionally uploads to Google Drive
    5. Updates status in Google Sheets (if configured)

    Returns:
        DownloadPDFResponse with file info, Drive URLs, and timing data
    """
    started = time.time()

    # Setup status tracker
    tracker = TaskStatusTracker(
        sheet_id=req.sheet_id,
        row=req.row,
        status_col=req.col,
    )

    # Prepare response object
    safe_folder = sanitize_folder_name(req.client_name).strip() or f"{req.kind}_{req.case_id}"
    response = DownloadPDFResponse(
        ok=False,
        kind=req.kind,
        case_id=req.case_id,
        subfolder=safe_folder,
        target_dir=str(config.DOWNLOAD_DIR / safe_folder),
        started_at=started,
        finished_at=started,
    )

    # Mark as running
    tracker.mark_running()

    try:
        # Use context manager for safe session handling
        with mycase_auto_session() as page:
            logger.info("Downloading %s PDFs for case %d (%s)", req.kind, req.case_id, req.client_name or "N/A")

            # Download PDFs
            result = download_pdfs(
                page=page,
                entity_id=req.case_id,
                entity_type=req.kind,
                subfolder=req.client_name,
            )

            response.target_dir = result["target_dir"]
            response.subfolder = safe_folder
            response.files_downloaded = result["count"]
            response.total_files_found = result["total_found"]
            response.local_files = result["files"]

        # Upload to Drive if configured
        drive_folder_url = None
        parent_drive_folder = req.drive_folder_id or config.DRIVE_DEFAULT_FOLDER_ID

        if parent_drive_folder and response.files_downloaded > 0:
            logger.info("Uploading %d files to Google Drive", response.files_downloaded)
            try:
                drive_info = upload_directory(
                    parent_id=parent_drive_folder,
                    local_dir=response.target_dir,
                    create_subfolder=True,
                    subfolder_name=safe_folder,
                )
                response.drive_parent_id = drive_info.get("parent_id")
                response.drive_target_folder_id = drive_info.get("target_folder_id")
                response.drive_files_count = drive_info.get("count")
                response.drive_files = [
                    DriveFileInfo(**f) for f in drive_info.get("files", [])
                ]
                # Construct folder URL
                if response.drive_target_folder_id:
                    drive_folder_url = f"https://drive.google.com/drive/folders/{response.drive_target_folder_id}"
                    response.drive_folder_url = drive_folder_url
                logger.info("Uploaded to Drive folder: %s", drive_folder_url)
            except Exception as e:
                logger.error("Failed to upload to Drive: %s", e)
                # Don't fail the whole operation, just log the error
                response.error = f"Download succeeded but Drive upload failed: {e}"

        # Mark success
        response.ok = True
        response.finished_at = time.time()
        tracker.mark_succeeded(result_url=drive_folder_url)

        logger.info(
            "Completed: %d/%d files downloaded in %.2fs",
            response.files_downloaded,
            response.total_files_found,
            response.finished_at - response.started_at,
        )

        return response

    except CaseNotFoundError as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed("NotFound", str(e))
        logger.error("Case not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))

    except AuthenticationError as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed("AuthError", str(e))
        logger.error("Authentication error: %s", e)
        raise HTTPException(status_code=401, detail=str(e))

    except DocumentDownloadError as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed("DownloadError", str(e))
        logger.error("Download error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed(type(e).__name__, str(e))
        logger.exception("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
