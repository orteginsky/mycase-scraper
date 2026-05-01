# scraping/documents.py
"""
Document download functionality for MyCase.
Handles both leads and court cases with unified logic.
"""
from pathlib import Path
from typing import Literal, List, Dict, Optional
from playwright.sync_api import Page

from src.core import config as settings
from src.core.exceptions import CaseNotFoundError, DocumentDownloadError
from src.utils.logger import get_logger
from src.utils.text_utils import sanitize_folder_name

logger = get_logger(__name__)


def _get_base_url(entity_type: Literal["lead", "case"]) -> str:
    """Get the base URL for the entity type."""
    if entity_type == "lead":
        return str(settings.BASE_LEADS_URL)
    return str(settings.BASE_CASE_URL)


def _navigate_to_documents(page: Page, entity_id: int, entity_type: Literal["lead", "case"]) -> None:
    """
    Navigate to the documents section for a lead or case.

    Args:
        page: Playwright page object
        entity_id: The ID of the lead or case
        entity_type: Either "lead" or "case"

    Raises:
        CaseNotFoundError: If the entity doesn't exist (404)
        DocumentDownloadError: If navigation fails
    """
    base_url = _get_base_url(entity_type)

    if entity_type == "lead":
        url = f"{base_url}/{entity_id}/case_details/info"
        logger.info("Opening lead page: %s", url)
        response = page.goto(url, wait_until="domcontentloaded")

        if not response or response.status == 404:
            raise CaseNotFoundError(entity_id, f"Lead {entity_id} not found (404)")

        # Click on documents tab for leads
        try:
            page.click("a#documents-tab")
            logger.info("Clicked on documents tab")
            page.wait_for_selector("table.files-table", timeout=10000)
            page.mouse.wheel(0, 2000)  # Scroll to load lazy content
            page.wait_for_selector("a.file-column-name-text", timeout=5000)
            page.wait_for_function(
                "document.querySelectorAll('table.files-table tr.Document').length > 0",
                timeout=5000
            )
        except Exception as e:
            raise DocumentDownloadError(f"Could not find documents table for lead {entity_id}: {e}")
    else:
        # Court case
        url = f"{base_url}/{entity_id}/case_details/documents#documents"
        logger.info("Opening case documents: %s", url)
        response = page.goto(url, wait_until="domcontentloaded")

        if not response or response.status == 404:
            raise CaseNotFoundError(entity_id, f"Case {entity_id} not found (404)")

        try:
            page.wait_for_selector("table.files-table", timeout=15000)
        except Exception as e:
            raise DocumentDownloadError(f"Could not find documents table for case {entity_id}: {e}")


def _extract_document_links(page: Page) -> List[Dict[str, str]]:
    """
    Extract all document links from the current page.

    Returns:
        List of dicts with 'text' (filename) and 'href' (URL)
    """
    links = page.eval_on_selector_all(
        "a.file-column-name-text",
        "els => els.map(e => ({text: e.textContent.trim(), href: e.getAttribute('href')}))"
    )
    return links


def _download_single_document(page: Page, doc_info: Dict[str, str], target_dir: Path) -> Optional[str]:
    """
    Download a single document from MyCase.

    Args:
        page: Playwright page object
        doc_info: Dict with 'text' (filename) and 'href' (URL)
        target_dir: Directory to save the file

    Returns:
        Path to saved file, or None if download failed
    """
    file_name = doc_info["text"]
    doc_url = doc_info["href"]

    if doc_url.startswith("/"):
        doc_url = f"{settings.MYCASE_BASE_URL}{doc_url}"

    logger.info("Opening document: %s", file_name)
    doc_page = page.context.new_page()

    try:
        doc_page.goto(doc_url, wait_until="domcontentloaded")

        # Wait for download button
        doc_page.wait_for_selector('a[href*="download"]', timeout=10000)
        with doc_page.expect_download() as download_info:
            doc_page.click('a[href*="download"]')
        download = download_info.value

        safe_path = target_dir / file_name
        download.save_as(str(safe_path))
        logger.info("Saved: %s", safe_path)
        return str(safe_path)

    except Exception as e:
        logger.warning("Could not download %s: %s", file_name, e)
        return None
    finally:
        doc_page.close()


def download_pdfs(
    page: Page,
    entity_id: int,
    entity_type: Literal["lead", "case"],
    subfolder: str,
) -> Dict:
    """
    Download all PDF documents from a MyCase lead or case.

    Args:
        page: Playwright page object (must be logged in)
        entity_id: The ID of the lead or court case
        entity_type: Either "lead" or "case"
        subfolder: Name of subfolder to save files (client name)

    Returns:
        Dict with:
            - entity_id: int
            - entity_type: str
            - target_dir: str (path to folder)
            - files: List[str] (paths to downloaded files)
            - count: int (number of files downloaded)
            - total_found: int (total documents found)

    Raises:
        CaseNotFoundError: If entity doesn't exist
        DocumentDownloadError: If navigation or download fails
    """
    # Sanitize subfolder name
    safe_subfolder = sanitize_folder_name(subfolder).strip()
    if not safe_subfolder:
        safe_subfolder = f"{entity_type}_{entity_id}"

    target_dir = settings.DOWNLOAD_DIR / safe_subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    # Navigate to documents section
    _navigate_to_documents(page, entity_id, entity_type)

    # Extract document links
    links = _extract_document_links(page)
    logger.info("Found %d documents for %s", len(links), safe_subfolder)

    # Download each document
    downloaded_files = []
    for link in links:
        file_path = _download_single_document(page, link, target_dir)
        if file_path:
            downloaded_files.append(file_path)

    logger.info("Downloaded %d/%d documents", len(downloaded_files), len(links))

    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "target_dir": str(target_dir),
        "files": downloaded_files,
        "count": len(downloaded_files),
        "total_found": len(links),
    }
