# api/endpoints/cases.py
"""
Endpoint for extracting case information from MyCase.
"""
import time
from fastapi import APIRouter, HTTPException

from src.api.schemas import CaseNameRequest, CaseNameResponse
from src.api.status_writer import TaskStatusTracker
from src.core import mycase_auto_session
from src.core.exceptions import CaseNotFoundError, ScrapingError, AuthenticationError
from src.scraping.cases import get_case_name
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.post("/get-name", response_model=CaseNameResponse)
def get_case_name_endpoint(req: CaseNameRequest) -> CaseNameResponse:
    """
    Extract the case name for a specific MyCase ID.

    This endpoint:
    1. Reuses or starts a MyCase session.
    2. Navigates to the case page.
    3. Extracts the name from the header.
    4. Updates status in Google Sheets (if tracking info is provided).

    Returns:
        CaseNameResponse with case data and metadata.
    """
    started = time.time()

    # Setup status tracker (optional tracking in Google Sheets)
    tracker = TaskStatusTracker(
        sheet_id=req.sheet_id,
        row=req.row,
        status_col=req.col,
    )

    # Prepare response
    response = CaseNameResponse(
        ok=False,
        case_id=req.case_id,
        started_at=started,
        finished_at=started,
    )

    # Mark as running in sheets
    tracker.mark_running()

    try:
        # Use existing context manager for managed session
        with mycase_auto_session() as page:
            logger.info("API Request: Extracting case name for ID %d", req.case_id)

            result = get_case_name(page, req.case_id)

            # Update response from service result
            response.case_name = result.get("case_name")
            response.url = result.get("url")
            response.extracted_at = result.get("extracted_at")
            response.ok = True

        # Mark success in sheets
        response.finished_at = time.time()
        tracker.mark_succeeded()

        logger.info(
            "Successfully extracted name for case %d in %.2fs",
            req.case_id,
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

    except ScrapingError as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed("ScrapingError", str(e))
        logger.error("Scraping error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed(type(e).__name__, str(e))
        logger.exception("Unexpected error in cases endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
