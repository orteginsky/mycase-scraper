# scraping/messaging.py
"""
Messaging functionality for MyCase.
Send text messages to clients through MyCase platform.
"""
import time
from typing import Dict, Any
from datetime import datetime
from playwright.sync_api import Page

from src.core import config as settings
from src.core.exceptions import CaseNotFoundError, MessageSendError
from src.utils.logger import get_logger

logger = get_logger(__name__)


def send_text_message(
    page: Page,
    case_id: int,
    message: str,
    wait_after_send: float = 2.0,
) -> Dict[str, Any]:
    """
    Send a text message to a client through MyCase.

    Args:
        page: Playwright page object (must be logged in)
        case_id: The court case ID
        message: The message text to send
        wait_after_send: Seconds to wait after sending (for stability)

    Returns:
        Dict with:
            - case_id: int
            - message_sent: str
            - sent_at: str (ISO timestamp)
            - success: bool

    Raises:
        CaseNotFoundError: If case doesn't exist
        MessageSendError: If message send fails
    """
    url = f"{settings.BASE_CASE_URL}/{case_id}/text_messages"
    logger.info("Opening text messages page: %s", url)

    response = page.goto(url, wait_until="domcontentloaded")

    if not response or response.status == 404:
        raise CaseNotFoundError(case_id, f"Case {case_id} not found (404)")

    result = {
        "case_id": case_id,
        "message_sent": message,
        "sent_at": None,
        "success": False,
    }

    try:
        # Wait for message textarea
        page.wait_for_selector(
            'textarea[name="message-textarea"]',
            state="visible",
            timeout=5000
        )

        # Type the message
        page.fill('textarea[name="message-textarea"]', message)
        logger.info("Typed message: %s", message[:50] + "..." if len(message) > 50 else message)

        # Send the message by pressing Enter
        page.press('textarea[name="message-textarea"]', "Enter")
        result["sent_at"] = datetime.utcnow().isoformat() + "Z"
        result["success"] = True

        logger.info("Message sent successfully to case %d", case_id)

        # Wait for message to be processed
        if wait_after_send > 0:
            time.sleep(wait_after_send)

    except Exception as e:
        logger.exception("Failed to send message to case %d: %s", case_id, e)
        raise MessageSendError(f"Could not send message to case {case_id}: {e}")

    return result


def verify_message_sent(page: Page, message_snippet: str) -> bool:
    """
    Verify that a message was successfully sent by checking if it appears in the chat.

    Args:
        page: Playwright page object (on text_messages page)
        message_snippet: Part of the message text to look for

    Returns:
        True if message found in chat, False otherwise
    """
    try:
        # Look for the message in the chat history
        messages = page.eval_on_selector_all(
            ".message-content, .chat-message-text",
            "els => els.map(e => e.textContent.trim())"
        )

        for msg in messages:
            if message_snippet in msg:
                return True
        return False

    except Exception as e:
        logger.warning("Could not verify message: %s", e)
        return False
