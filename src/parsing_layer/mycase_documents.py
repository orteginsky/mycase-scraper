#parsinfg_layer/mycase_documents.py
import os

from typing import Optional
from pathlib import Path
from playwright.sync_api import Page
from config.settings import BASE_CASE_URL, DOWNLOAD_DIR, BASE_LEADS_URL
from utils.logger import get_logger

logger = get_logger(__name__)


def download_case_pdfs(page: Page, case_id: int, subfolder: str):
    """
    Abre la página de documentos de un caso y descarga los PDFs en
    DOWNLOAD_DIR/subfolder. Si el ID no existe (404) se imprime un aviso
    y se salta al siguiente.
    """
    url = f"{BASE_CASE_URL}/{case_id}/case_details/documents#documents"
    logger.info(f"➡️  Abriendo: {url}")

    # 1️⃣ Ir a la página y capturar la respuesta
    response = page.goto(url, wait_until="domcontentloaded")

    # 2️⃣ Comprobar si el servidor devolvió 404
    if not response or response.status == 404:
        logger.info(f"⚠️  ID {case_id} no existe (404). Se omite.")
        return  # Saltar este ID

    # 3️⃣ Esperar la tabla de archivos (si no está, también se omite)
    try:
        page.wait_for_selector("table.files-table", timeout=15000)
    except Exception:
        logger.error(f"⚠️  No se encontró la tabla de archivos para ID {case_id}. Se omite.")
        return

    # 4️⃣ Crear carpeta de cliente
    safe_subfolder = subfolder.replace("/", "_").replace("\\", "_").strip()
    if not safe_subfolder:
        safe_subfolder = f"case_{case_id}"
    target_dir = Path(DOWNLOAD_DIR) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    # 5️⃣ Extraer enlaces de documentos
    links = page.eval_on_selector_all(
        "a.file-column-name-text",
        "els => els.map(e => ({text: e.textContent.trim(), href: e.getAttribute('href')}))"
    )
    logger.info(f"📂 {len(links)} archivos encontrados para {subfolder}.")

    # 6️⃣ Descargar cada documento
    for link in links:
        file_name = link["text"]
        doc_url = link["href"]
        if doc_url.startswith("/"):
            doc_url = f"https://the-mendoza-law-firm.mycase.com{doc_url}"

        logger.info(f"⬇️  Abriendo documento: {file_name}")
        doc_page = page.context.new_page()
        doc_page.goto(doc_url, wait_until="domcontentloaded")

        try:
            # Esperar botón de descarga (10 s)
            doc_page.wait_for_selector('a[href*="download"]', timeout=10000)
            with doc_page.expect_download() as download_info:
                doc_page.click('a[href*="download"]')
            download = download_info.value

            safe_path = target_dir / file_name
            download.save_as(str(safe_path))
            logger.info(f"✅ Guardado en {safe_path}")
        except Exception:
            logger.warning(f"⚠️  No se encontró botón de descarga para {file_name}. Se omite.")
        finally:
            doc_page.close()


def download_leads_pdfs(page: Page, case_id: Optional[int], subfolder: str):
    """
    Abre la pestaña de documentos de un lead y descarga los PDFs en
    DOWNLOAD_DIR/subfolder. Si el ID no existe (404) se imprime un aviso
    y se salta al siguiente.
    """
    url = f"{BASE_LEADS_URL}/{case_id}/case_details/info"
    logger.info(f"➡️  Abriendo: {url}")

    # 1️⃣ Navegar a la página principal del lead
    response = page.goto(url, wait_until="domcontentloaded")

    # 2️⃣ Comprobar si existe el ID (404)
    if not response or response.status == 404:
        logger.info(f"⚠️  ID {case_id} no existe (404). Se omite.")
        return

    # 3️⃣ Ir a la pestaña de Documentos y esperar la tabla
    try:
        # Hacer clic en el tab de documentos
        page.click('a#documents-tab')
        logger.info("➡️  Abriendo pestaña de documentos...")
        page.wait_for_selector("table.files-table", timeout=10000)
        page.mouse.wheel(0, 2000)
        page.wait_for_selector("a.file-column-name-text", timeout=5000)
        page.wait_for_function(
            "document.querySelectorAll('table.files-table tr.Document').length > 0",
            timeout=5000
        )
    except Exception:
        logger.warning(f"⚠️  No se encontró la tabla de archivos para ID {case_id}. Se omite.")
        return


    # 4️⃣ Crear carpeta de cliente
    safe_subfolder = subfolder.replace("/", "_").replace("\\", "_").strip()
    if not safe_subfolder:
        safe_subfolder = f"case_{case_id}"

    target_dir = Path(DOWNLOAD_DIR) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    # 5️⃣ Extraer enlaces de documentos PDF
    links = page.eval_on_selector_all(
        "a.file-column-name-text",
        "els => els.map(e => ({text: e.textContent.trim(), href: e.getAttribute('href')}))"
        )
    logger.info(f"📂 {len(links)} archivos encontrados para {subfolder}.")


    # 6️⃣ Descargar cada documento
    for link in links:
        file_name = link["text"]
        doc_url = link["href"]
        if doc_url.startswith("/"):
            doc_url = f"https://the-mendoza-law-firm.mycase.com{doc_url}"

        logger.info(f"⬇️  Abriendo documento: {file_name}")
        doc_page = page.context.new_page()
        doc_page.goto(doc_url, wait_until="domcontentloaded")

        try:
            # Esperar botón de descarga (10 s)
            doc_page.wait_for_selector('a[href*="download"]', timeout=10000)
            with doc_page.expect_download() as download_info:
                doc_page.click('a[href*="download"]')
            download = download_info.value

            safe_path = target_dir / file_name
            download.save_as(str(safe_path))
            logger.info(f"✅ Guardado en {safe_path}")
        except Exception:
            logger.warning(f"⚠️  No se encontró botón de descarga para {file_name}. Se omite.")
        finally:
            doc_page.close()