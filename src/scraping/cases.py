# src/scraping/cases.py
"""
Case-related scraping functionality for MyCase.
"""
from typing import Dict, Optional, Any
from playwright.sync_api import Page
from datetime import datetime

from src.core import config as settings
from src.core.exceptions import CaseNotFoundError, ScrapingError
from src.utils.logger import get_logger

logger = get_logger(__name__)

def get_case_name(page: Page, case_id: int) -> Dict[str, Any]:
    """
    Extract the case name for a specific MyCase ID.
    
    Args:
        page: Playwright page object (must be logged in)
        case_id: The court case ID
        
    Returns:
        Dict with case_name, url, and extracted_at.
    """
    url = f"{settings.BASE_CASE_URL}/{case_id}/notes"
    logger.info("Navigating to case notes to extract name: %s", url)
    
    try:
        response = page.goto(url, wait_until="domcontentloaded")
        
        if not response or response.status == 404:
            raise CaseNotFoundError(case_id, f"Case {case_id} not found (404)")
            
        case_name = None
        name_el = page.query_selector("#case-name-header, h1.case-name, .case-header h1")
        if name_el:
            case_name = name_el.inner_text().strip()
            
        return {
            "case_id": case_id,
            "case_name": case_name,
            "url": url,
            "extracted_at": datetime.utcnow().isoformat() + "Z",
        }
        
    except CaseNotFoundError:
        raise
    except Exception as e:
        logger.exception("Error extracting case name for %d: %s", case_id, e)
        raise ScrapingError(f"Failed to extract case name for {case_id}: {e}")
