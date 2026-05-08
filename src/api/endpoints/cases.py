# api/endpoints/cases.py
"""
Endpoint for extracting case information from MyCase.
"""
import re
import time
import unicodedata
from fastapi import APIRouter, HTTPException
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.api.schemas import CaseNameRequest, CaseNameResponse, RunCaseNamesBatchRequest, RunCaseNamesBatchResponse
from src.api.status_writer import TaskStatusTracker
from src.clients.sheets_client import read_range, write_single_cell, col_to_a1
from src.core import mycase_auto_session
from src.core import config
from src.core.exceptions import CaseNotFoundError, ScrapingError, AuthenticationError
from src.scraping.cases import get_case_name
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.post("/get-name", response_model=CaseNameResponse)
def get_case_name_endpoint(req: CaseNameRequest) -> CaseNameResponse:
    """
    Extract the case name for a specific MyCase ID.

    This endpoint:
    1. Reuses or starts a MyCase session.
    2. Navigates to the case page.
    3. Extracts the name from the header.
    4. Updates status in Google Sheets (if tracking info is provided).

    Returns:
        CaseNameResponse with case data and metadata.
    """
    started = time.time()

    # Setup status tracker (optional tracking in Google Sheets)
    tracker = TaskStatusTracker(
        sheet_id=req.sheet_id,
        row=req.row,
        status_col=req.col,
    )

    # Prepare response
    response = CaseNameResponse(
        ok=False,
        case_id=req.case_id,
        started_at=started,
        finished_at=started,
    )

    # Mark as running in sheets
    tracker.mark_running()

    try:
        # Use existing context manager for managed session
        with mycase_auto_session() as page:
            logger.info("API Request: Extracting case name for ID %d", req.case_id)

            result = get_case_name(page, req.case_id)

            # Update response from service result
            response.case_name = result.get("case_name")
            response.url = result.get("url")
            response.extracted_at = result.get("extracted_at")
            response.ok = True

        # Mark success in sheets
        response.finished_at = time.time()
        tracker.mark_succeeded()

        logger.info(
            "Successfully extracted name for case %d in %.2fs",
            req.case_id,
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

    except ScrapingError as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed("ScrapingError", str(e))
        logger.error("Scraping error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        response.error = str(e)
        response.finished_at = time.time()
        tracker.mark_failed(type(e).__name__, str(e))
        logger.exception("Unexpected error in cases endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Helpers for run-batch ─────────────────────────────────────────────────────

_COL_B = 2   # nombre original (validación)
_COL_U = 21  # URL de MyCase
_COL_R = 18  # nombre extraído (resultado)
_COL_W = 23  # flag "revisar"

_COL_R_A1 = col_to_a1(_COL_R)  # "R"
_COL_W_A1 = col_to_a1(_COL_W)  # "W"


def _extract_case_url_id(url: str) -> str | None:
    match = re.search(r"/court_cases/(\d+)/", url)
    return match.group(1) if match else None


def _clean_name(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\(.*?\)", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if c.isalpha())
    return text.upper()


def _scrape_case_name(page, url: str) -> str:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        locator = page.locator("#case-name-header.test-case-name-header")
        locator.wait_for(state="visible", timeout=10_000)
        return locator.text_content().strip()
    except PlaywrightTimeoutError:
        logger.warning("Timeout al navegar: %s", url)
        return "Not Found"
    except Exception as exc:
        logger.error("Error inesperado en %s: %s", url, exc)
        return "Error"


# ── Batch endpoint ────────────────────────────────────────────────────────────

@router.post("/run-batch", response_model=RunCaseNamesBatchResponse)
def run_case_names_batch(req: RunCaseNamesBatchRequest) -> RunCaseNamesBatchResponse:
    """
    Lee la columna U (URLs de MyCase) del Google Sheet configurado,
    extrae el nombre de cada caso pendiente (col R vacía) y escribe
    el resultado en col R. Si el nombre no coincide con col B, marca
    col W con 'revisar'.
    """
    started = time.time()
    spreadsheet_id = req.spreadsheet_id or config.CASE_NAMES_SPREADSHEET_ID
    sheet_name = req.sheet_name or config.CASE_NAMES_SHEET_NAME

    response = RunCaseNamesBatchResponse(ok=False, started_at=started, finished_at=started)

    try:
        logger.info("Leyendo hoja '%s' del spreadsheet %s", sheet_name, spreadsheet_id)
        data = read_range(sheet_id=spreadsheet_id, sheet_name=sheet_name, range_notation="A:W")

        if not data or len(data) < 2:
            logger.info("Sin datos o solo encabezado, nada que procesar.")
            response.ok = True
            response.finished_at = time.time()
            return response

        # Identificar filas pendientes: col U tiene URL y col R está vacía
        pending: list[tuple[int, str, str]] = []  # (sheet_row, url, original_name_b)
        for i, row in enumerate(data):
            if i == 0:
                continue
            col_b = row[_COL_B - 1].strip() if len(row) >= _COL_B else ""
            col_u = row[_COL_U - 1].strip() if len(row) >= _COL_U else ""
            col_r = row[_COL_R - 1].strip() if len(row) >= _COL_R else ""
            if col_u and not col_r:
                pending.append((i + 1, col_u, col_b))

        if not pending:
            logger.info("No hay filas pendientes (col R ya completa o col U vacía).")
            response.ok = True
            response.finished_at = time.time()
            return response

        logger.info("Filas pendientes: %d", len(pending))

        with mycase_auto_session() as page:
            for sheet_row, url, original_name_b in pending:
                case_url_id = _extract_case_url_id(url)
                if not case_url_id:
                    logger.warning("Fila %d: no se pudo extraer ID desde '%s'", sheet_row, url)
                    response.total_skipped += 1
                    continue

                logger.info("Fila %d | ID: %s", sheet_row, case_url_id)
                case_name = _scrape_case_name(page, url)

                write_single_cell(
                    sheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    a1_range=f"{_COL_R_A1}{sheet_row}",
                    value=case_name,
                )
                logger.info("✓ Escrito en R%d: %s", sheet_row, case_name)

                if case_name in ("Not Found", "Error"):
                    response.total_errors += 1
                    continue

                response.total_ok += 1

                # Validación contra col B
                if _clean_name(case_name) != _clean_name(original_name_b):
                    write_single_cell(
                        sheet_id=spreadsheet_id,
                        sheet_name=sheet_name,
                        a1_range=f"{_COL_W_A1}{sheet_row}",
                        value="revisar",
                    )
                    logger.warning(
                        "⚠ Validación fallida fila %d: '%s' vs '%s'. Marcado 'revisar'.",
                        sheet_row, case_name, original_name_b,
                    )

        response.ok = True
        response.finished_at = time.time()
        logger.info(
            "===== TOTAL — OK: %d | Errores: %d | Omitidas: %d =====",
            response.total_ok, response.total_errors, response.total_skipped,
        )
        return response

    except AuthenticationError as e:
        response.error = str(e)
        response.finished_at = time.time()
        logger.error("Auth error en case-names batch: %s", e)
        raise HTTPException(status_code=401, detail=str(e))

    except Exception as e:
        response.error = str(e)
        response.finished_at = time.time()
        logger.exception("Error inesperado en case-names batch: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
