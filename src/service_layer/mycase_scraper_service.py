# service_layer/mycase_scraper_service.py
from playwright.sync_api import TimeoutError as PlaywrightTimeout, Page
from config.settings import BASE_CASE_URL
from utils.logger import get_logger
import re

logger = get_logger(__name__)

def get_case_details(page: Page, case_id: int) -> dict:
    """
    Extrae Name, ID, Date opened y Type of case de la página de notas de un caso.
    Requiere una sesión activa de Playwright (ya logueada).
    """
    url = f"{BASE_CASE_URL}/{case_id}/notes"

    try:
        logger.info(f"🌐 Accediendo a {url}")
        page.goto(url, timeout=25000)
        page.wait_for_selector("#case-name-header", timeout=1000)

        # 1️⃣ Name
        name = page.locator("#case-name-header").inner_text().strip()

        # 2️⃣ ID (limpiando todo lo que esté después de //)
        id_raw = page.locator("#court-case-number-header").inner_text().strip()
        case_id_clean = re.split(r"//", id_raw)[0].strip()

        # 3️⃣ Date opened
        date_opened_locator = page.locator("xpath=//span[contains(text(), 'Date opened:')]/..")
        date_opened = date_opened_locator.inner_text().replace("Date opened:", "").strip()

        # 4️⃣ Type of case
        practice_area_locator = page.locator("xpath=//span[contains(text(), 'Practice area:')]/..")
        type_of_case = practice_area_locator.inner_text().replace("Practice area:", "").strip()

        logger.info(f"✅ Extraído {name} | {case_id_clean} | {date_opened} | {type_of_case}")

        return {
            "Name": name,
            "ID": case_id_clean,
            "DateOpened": date_opened,
            "TypeOfCase": type_of_case
        }

    except PlaywrightTimeout:
        logger.error(f"❌ Timeout accediendo al caso {case_id}")
        return {"Name": None, "ID": case_id, "DateOpened": None, "TypeOfCase": None}

    except Exception as e:
        logger.exception(f"⚠️ Error procesando el caso {case_id}: {e}")
        return {"Name": None, "ID": case_id, "DateOpened": None, "TypeOfCase": None}
