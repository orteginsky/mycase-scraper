# src/scraping/case_stages.py
"""
Case Stage update scraping logic for MyCase.
Migrated from MendozaFirm_IA/Projects/Docker/Psy/psy_case_stage.py
"""
from typing import Optional, List

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.core import config as settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

STAGE_MAP = {
    "FULLY": "FULLY RFA",
    "FULLY SIN RAPSHEET": "SEMI RFA",
}

STATUS_COL_NAME = "STATUS FULLY"
ID_COL_NAME = "ID"
MYCASE_STATUS_COL_NAME = "Actualización MyCase"
STATUS_PROCESADO = "Procesado"


def get_column_index(headers: list, col_name: str) -> Optional[int]:
    """Return the 0-based index of col_name in headers (case-insensitive), or None."""
    target = col_name.lower().strip()
    for i, h in enumerate(headers):
        if str(h).lower().strip() == target:
            return i
    return None


def get_target_stage(status_value: str) -> Optional[str]:
    """Return the MyCase stage label for a STATUS FULLY value, or None if not in STAGE_MAP."""
    return STAGE_MAP.get(status_value.strip())


def update_case_stage(page: Page, case_id: int, target_stage: str) -> bool:
    """
    Navigate to the case info page and update the Case Stage dropdown via the inline editor.

    Returns True on success, False on any timeout or unexpected error.
    """
    url = f"{settings.BASE_CASE_URL}/{case_id}/info"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Use 'attached' (not 'visible') — CSS is blocked so computed visibility is unreliable
        editor = page.locator(".case-stage-inline-editor")
        editor.wait_for(state="attached", timeout=10000)
        editor.click()

        # Skip .editing class check entirely — wait directly for the actionable element
        select = page.locator('select[name="case-stage-select"]')
        select.wait_for(state="attached", timeout=12000)
        select.select_option(label=target_stage)

        # Save confirmation: select disappears from DOM after save
        select.wait_for(state="detached", timeout=10000)

        logger.info("[CASE_STAGE] ID %s → '%s' ✓", case_id, target_stage)
        return True

    except PlaywrightTimeoutError as e:
        logger.warning("[CASE_STAGE] Timeout para ID %s: %s", case_id, e)
        return False
    except Exception as e:
        logger.error("[CASE_STAGE] Error inesperado para ID %s: %s", case_id, e)
        return False
