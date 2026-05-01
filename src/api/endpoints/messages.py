# api/endpoints/messages.py
"""
Endpoint for sending text messages through MyCase.
"""
import time
from fastapi import APIRouter, HTTPException

from src.api.schemas import SendMessageRequest, SendMessageResponse
from src.api.status_writer import TaskStatusTracker
from src.core import mycase_auto_session
from src.core.exceptions import CaseNotFoundError, MessageSendError, AuthenticationError
from src.scraping.messages import send_text_message, verify_message_sent
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("/send", response_model=SendMessageResponse)
def send_message_endpoint(req: SendMessageRequest) -> SendMessageResponse:
    """
    Send a text message to a client through MyCase.

    This endpoint:
    1. Logs into MyCase (uses persistent session)
    2. Navigates to the case's text messages section
    3. Types and sends the message
    4. Optionally verifies the message was sent
    5. Updates status in Google Sheets (if configured)

    Returns:
        SendMessageResponse with send confirmation and timing
    """
    started = time.time()

    # Setup status tracker
    tracker = TaskStatusTracker(
        sheet_id=req.sheet_id,
        row=req.row,
        status_col=req.col,
    )

    # Prepare response
    response = SendMessageResponse(
        ok=False,
        case_id=req.case_id,
        client_name=req.client_name,
        message_sent=req.message,
        sent_at="",
        started_at=started,
        finished_at=started,
        verified=True,   
    )

    # Mark as running
    tracker.mark_running()

    try:
        # Send message using context manager
        with mycase_auto_session() as page:
            logger.info(
                "Sending message to case %d: %s",
                req.case_id,
                req.message[:50] + "..." if len(req.message) > 50 else req.message,
            )

            result = send_text_message(
                page=page,
                case_id=req.case_id,
                message=req.message,
            )

            response.sent_at = result.get("sent_at")

            # Verify if requested
            if req.verify_sent:
                # Take a snippet of the message for verification
                snippet = req.message[:30] if len(req.message) > 30 else req.message
                response.verified = verify_message_sent(page, snippet)
                if not response.verified:
                    logger.warning("Message not verified in chat history")

        # Mark success
        response.ok = True
        response.finished_at = time.time()
        tracker.mark_succeeded()

        logger.info(
            "Message sent successfully in %.2fs",
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

    except MessageSendError as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed("SendError", str(e))
        logger.error("Message send error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed(type(e).__name__, str(e))
        logger.exception("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
