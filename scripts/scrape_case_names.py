"""
Script: scrape_case_names.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lee URLs de la columna U de un Google Sheet, extrae el
nombre del caso desde MyCase y lo escribe en la columna R.

Usa playwright_driver.create_playwright_context() en lugar de
playwright_handler, lo que permite aprovechar:
  - PW_STATE_B64  → sesión desde variable de entorno (Docker/CI)
  - Perfil en disco → sesión persistente local

Uso:
    python -m src.scripts.scrape_case_names

Prerequisitos:
  - Sesión activa en state.json  (ejecutar crear_sesion primero)
    O bien PW_STATE_B64 configurada en .env
  - sa_key.json en la raíz del proyecto
  - Variables MYCASE_EMAIL / MYCASE_PASSWORD en .env (sólo
    se usan como validación; la sesión ya viene del state)
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

# ── Cargar .env desde la raíz del proyecto ───────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=_ROOT / ".env")

import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.core.context_manager import mycase_auto_session
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Google Sheets config
# ---------------------------------------------------------------------------
SHEET_ID    = "1HS6QJfEQsKYHP8MBAtu2cpnjc7I-5ph1C5blWqCOuZQ"
SA_KEY_PATH = _ROOT / "sa_key.json"

COL_B  = 2   # columna B  → nombre original para comparar
COL_U  = 21  # columna U  → URLs de los casos
COL_R  = 18  # columna R  → donde se escribe el nombre extraído
COL_W  = 23  # columna W  → donde se pone 'revisar' si no coinciden

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_sheet() -> gspread.Worksheet:
    """Devuelve la hoja 'MES ACTUAL' del Google Sheet usando la cuenta de servicio."""
    creds  = Credentials.from_service_account_file(str(SA_KEY_PATH), scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet("MES ACTUAL")


def extract_case_id(url: str) -> str | None:
    """Extrae el ID numérico del caso desde una URL de MyCase.

    Ejemplo: https://the-mendoza-law-firm.mycase.com/court_cases/40693908/items
             → '40693908'
    """
    match = re.search(r"/court_cases/(\d+)/", url)
    return match.group(1) if match else None


def clean_name(text: str) -> str:
    """Limpia el nombre para comparación:
    1. Elimina paréntesis y su contenido.
    2. Pasa a unicode (normalización NFKD).
    3. Quita todo lo que no sea letra.
    4. Pasa a mayúsculas.
    """
    if not text:
        return ""
    # Eliminar lo que esté entre paréntesis, incluyendo los paréntesis
    text = re.sub(r"\(.*?\)", "", text)
    # Normalizar Unicode (NFKD separa acentos de letras base)
    text = unicodedata.normalize("NFKD", text)
    # Quitar caracteres que no sean letras
    text = "".join(c for c in text if c.isalpha())
    # Pasar a mayúsculas
    return text.upper()


def obtener_case_name(page, url: str) -> str:
    """Navega a la URL del caso y extrae el nombre del elemento #case-name-header."""
    logger.info("Navegando a: %s", url)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        case_locator = page.locator("#case-name-header.test-case-name-header")
        case_locator.wait_for(state="visible", timeout=10_000)

        case_name = case_locator.text_content()
        return case_name.strip()

    except PlaywrightTimeoutError:
        logger.warning("Timeout para la URL: %s", url)
        return "Not Found"
    except Exception as e:
        logger.error("Error inesperado para la URL: %s — %s", url, e)
        return "Error"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # 1. Conectar a Google Sheets
    logger.info("Conectando a Google Sheets...")
    sheet    = get_sheet()
    all_rows = sheet.get_all_values()
    logger.info("Total de filas en la hoja: %d", len(all_rows))

    # 2. Identificar filas pendientes:
    #    - Columna U tiene URL de MyCase
    #    - Columna R está vacía (aún no procesada)
    pending: list[tuple[int, str, str]] = []  # (row_number, url, original_name_col_b)

    for i, row in enumerate(all_rows):
        if i == 0:
            continue  # saltar cabecera

        col_b_val = row[COL_B - 1].strip() if len(row) >= COL_B else ""
        col_u_val = row[COL_U - 1].strip() if len(row) >= COL_U else ""
        col_r_val = row[COL_R - 1].strip() if len(row) >= COL_R else ""

        # Solo procesamos si no hay nombre (R vacío) y hay URL (U)
        if col_u_val and not col_r_val:
            pending.append((i + 1, col_u_val, col_b_val))

    if not pending:
        logger.info(
            "No hay filas pendientes de procesar "
            "(columna R ya completa o columna U vacía)."
        )
        return

    logger.info("Filas pendientes de procesar: %d", len(pending))

    # 3. Iniciar Playwright usando el context manager unificado
    errores: int = 0
    ids_no_encontrados: list[str] = []

    try:
        with mycase_auto_session() as page:
            for sheet_row, url, original_name_b in pending:
                case_id = extract_case_id(url)
                if not case_id:
                    logger.warning(
                        "Fila %d: No se pudo extraer el ID desde '%s'", sheet_row, url
                    )
                    errores += 1
                    continue

                logger.info("Fila %d | ID: %s", sheet_row, case_id)
                case_name = obtener_case_name(page, url)

                if case_name in ("Not Found", "Error"):
                    errores += 1
                    ids_no_encontrados.append(case_id)

                # Escribir resultado en columna R
                sheet.update_cell(sheet_row, COL_R, case_name)
                logger.info("✓ Escrito en R%d: %s", sheet_row, case_name)

                # Validación con columna B
                if case_name not in ("Not Found", "Error"):
                    cleaned_scraped = clean_name(case_name)
                    cleaned_original = clean_name(original_name_b)

                    if cleaned_scraped != cleaned_original:
                        sheet.update_cell(sheet_row, COL_W, "revisar")
                        logger.warning(
                            "⚠ Validación fallida en fila %d: '%s' vs '%s'. Marcado 'revisar'.",
                            sheet_row, cleaned_scraped, cleaned_original
                        )
                    else:
                        logger.info("✓ Validación OK en fila %d.", sheet_row)
    except Exception as e:
        logger.error("Error crítico durante el procesamiento: %s", e)

    # 4. Resumen
    logger.info("=== Proceso completado ===")
    logger.info("IDs no encontrados o con error: %s", ids_no_encontrados)
    logger.info("Errores totales: %d", errores)


if __name__ == "__main__":
    main()
