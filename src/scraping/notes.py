# scraping/notes.py
"""
Notes extraction functionality for MyCase.
Extracted and parsed according to specific UI requirements.
"""
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
from src.core import config as settings
from src.utils.logger import get_logger
from src.parsers.mycase_notes_parser import parse_notes_html

logger = get_logger(__name__)

def extract_case_notes(
    page: Page,
    entity_id: int,
    entity_type: str = "case",
    type: str = None,
) -> Dict[str, Any]:
    """
    Navega a la URL de notas (lead o case), expande el contenido truncado y extrae la información.

    Args:
        page: Playwright page object (must be logged in)
        entity_id: The ID of the lead or court case
        entity_type: "case" o "lead"
        type: Informational parameter to be passed through

    Returns:
        Dict: Dictionary containing 'notes' (list) and 'type' (str).
    """
    if entity_type == "lead":
        base_url = settings.BASE_LEADS_URL
    else:
        base_url = settings.BASE_CASE_URL

    notes_url = f"{base_url}/{entity_id}/notes"
    logger.info("Navegando a la URL de notas: %s", notes_url)

    # 1. Navegar a la URL de notas
    response = page.goto(notes_url, wait_until="domcontentloaded")
    
    if not response or response.status == 404:
        logger.error("No se pudo cargar la página de notas para el caso %s (404)", entity_id)
        return []

    # Esperar a que la tabla de notas sea visible
    try:
        page.wait_for_selector("tr.notes_item", timeout=10000)
    except Exception:
        logger.warning("No se encontraron elementos 'tr.notes_item' en la página.")
        # Podría ser que no haya notas, retornamos lista vacía
        return []

    # 2. Identificar y hacer clic en todos los botones "Read more" (button.expand-notes)
    try:
        expand_buttons = page.query_selector_all("button.expand-notes")
        if expand_buttons:
            logger.info("Expandiendo %d notas truncadas...", len(expand_buttons))
            for btn in expand_buttons:
                if btn.is_visible():
                    try:
                        btn.click()
                        # Un pequeño delay para permitir que el contenido se expanda si es asíncrono
                        # aunque lo ideal es esperar a un cambio en el DOM si es necesario.
                        # page.wait_for_timeout(100) 
                    except Exception as e:
                        logger.debug("No se pudo hacer clic en un botón de expansión: %s", e)
        
        # Opcional: esperar un momento corto para asegurar que todas las expansiones terminaron
        page.wait_for_timeout(500)
        
    except Exception as e:
        logger.warning("Ocurrió un error al intentar expandir las notas: %s", e)

    # 3. Retornar la lista de notas procesada usando el parser
    html_content = page.content()
    notes = parse_notes_html(html_content)
    
    logger.info("Se extrajeron %d notas para el caso %s", len(notes), entity_id)
    return {
        "notes": notes,
        "type": type
    }


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
    url = f"{settings.BASE_CASE_URL}/{case_id}/notes"
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

        # Extract fields with improved selectors
        name = None
        case_id_val = str(case_id)
        date_opened = None
        type_of_case = None

        try:
            name_el = page.query_selector("#case-name-header, h1.case-name, .case-header h1")
            if name_el:
                name = name_el.inner_text().strip()
        except Exception:
            pass

        try:
            id_el = page.query_selector("#court-case-number-header")
            if id_el:
                case_id_val = id_el.inner_text().split("//")[0].strip()
        except Exception:
            pass

        try:
            date_el = page.locator("xpath=//span[contains(text(), 'Date opened:')]/..")
            if date_el.count() > 0:
                date_opened = date_el.first.inner_text().replace("Date opened:", "").strip()
        except Exception:
            pass

        try:
            type_el = page.locator("xpath=//span[contains(text(), 'Practice area:')]/..")
            if type_el.count() > 0:
                type_of_case = type_el.first.inner_text().replace("Practice area:", "").strip()
        except Exception:
            pass

        return {
            "Name": name,
            "ID": case_id_val,
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
