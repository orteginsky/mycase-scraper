# scraping/notes.py
"""
Notes extraction functionality for MyCase.
Extracts case notes and metadata from court cases and leads.
"""
from typing import Dict, List, Optional, Any, Literal
from playwright.sync_api import Page
from datetime import datetime

from core import config
from core.exceptions import CaseNotFoundError, ScrapingError
from utils.logger import get_logger

logger = get_logger(__name__)


def extract_case_notes(
    page: Page,
    entity_id: int,
    entity_type: Literal["lead", "case"] = "case",
) -> Dict[str, Any]:
    """
    Extract notes and metadata from a MyCase case or lead.

    Args:
        page: Playwright page object (must be logged in)
        entity_id: The ID of the lead or court case
        entity_type: Either "lead" or "case"

    Returns:
        Dict with:
            - entity_id: int
            - entity_type: str
            - case_name: str
            - date_opened: str (if available)
            - case_type: str (if available)
            - notes: List[Dict] with note content
            - extracted_at: str (ISO timestamp)

    Raises:
        CaseNotFoundError: If entity doesn't exist
        ScrapingError: If extraction fails
    """
    if entity_type == "lead":
        base_url = config.BASE_LEADS_URL
        notes_url = f"{base_url}/{entity_id}/notes"
    else:
        base_url = config.BASE_CASE_URL
        notes_url = f"{base_url}/{entity_id}/notes"

    logger.info("Extracting notes from: %s", notes_url)

    response = page.goto(notes_url, wait_until="domcontentloaded")

    if not response or response.status == 404:
        raise CaseNotFoundError(entity_id, f"{entity_type.capitalize()} {entity_id} not found (404)")

    result = {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "case_name": None,
        "date_opened": None,
        "case_type": None,
        "notes": [],
        "extracted_at": datetime.utcnow().isoformat() + "Z",
    }

    # Extract case metadata
    try:
        # Case name from header
        name_selector = "h1.case-name, .case-header h1, .lead-name"
        if page.query_selector(name_selector):
            result["case_name"] = page.text_content(name_selector).strip()
            logger.debug("Found case name: %s", result["case_name"])

        # Date opened (if visible)
        date_selector = ".case-opened-date, .date-opened"
        if page.query_selector(date_selector):
            result["date_opened"] = page.text_content(date_selector).strip()

        # Case type
        type_selector = ".case-type, .matter-type"
        if page.query_selector(type_selector):
            result["case_type"] = page.text_content(type_selector).strip()

    except Exception as e:
        logger.warning("Could not extract all metadata: %s", e)

    # Extract notes
    try:
        # Wait for notes to load
        page.wait_for_selector(".notes-list, .note-item, #notes-container", timeout=10000)

        # Extract each note
        notes = page.eval_on_selector_all(
            ".note-item, .note-entry, [data-note-id]",
            """
            els => els.map(el => {
                const content = el.querySelector('.note-content, .note-body, .note-text');
                const author = el.querySelector('.note-author, .author-name');
                const date = el.querySelector('.note-date, .note-timestamp, time');
                return {
                    content: content ? content.textContent.trim() : '',
                    author: author ? author.textContent.trim() : '',
                    date: date ? (date.getAttribute('datetime') || date.textContent.trim()) : '',
                };
            })
            """
        )

        result["notes"] = [n for n in notes if n.get("content")]
        logger.info("Extracted %d notes", len(result["notes"]))

    except Exception as e:
        logger.warning("Could not extract notes: %s", e)
        # Return what we have even if notes extraction fails
        result["notes"] = []

    return result


def extract_case_details(
    page: Page,
    case_id: int,
) -> Dict[str, Optional[str]]:
    """
    Extract basic case details (name, ID, date, type).
    Simplified version for metadata only.

    Args:
        page: Playwright page object
        case_id: The court case ID

    Returns:
        Dict with case metadata fields (may contain None values)
    """
    url = f"{config.BASE_CASE_URL}/{case_id}/notes"
    logger.info("Extracting case details from: %s", url)

    try:
        response = page.goto(url, wait_until="domcontentloaded")

        if not response or response.status == 404:
            logger.warning("Case %d not found", case_id)
            return {
                "Name": None,
                "ID": str(case_id),
                "DateOpened": None,
                "TypeOfCase": None,
            }

        # Extract fields with fallbacks
        name = None
        date_opened = None
        type_of_case = None

        try:
            name_el = page.query_selector("h1.case-name, .case-header h1")
            if name_el:
                name = name_el.text_content().strip()
        except Exception:
            pass

        try:
            date_el = page.query_selector(".case-opened-date, .date-opened")
            if date_el:
                date_opened = date_el.text_content().strip()
        except Exception:
            pass

        try:
            type_el = page.query_selector(".case-type, .matter-type")
            if type_el:
                type_of_case = type_el.text_content().strip()
        except Exception:
            pass

        return {
            "Name": name,
            "ID": str(case_id),
            "DateOpened": date_opened,
            "TypeOfCase": type_of_case,
        }

    except Exception as e:
        logger.exception("Error extracting case details for %d: %s", case_id, e)
        return {
            "Name": None,
            "ID": str(case_id),
            "DateOpened": None,
            "TypeOfCase": None,
        }
