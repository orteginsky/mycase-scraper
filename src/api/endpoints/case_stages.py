# src/api/endpoints/case_stages.py
"""
Endpoint for batch-updating Case Stage in MyCase from Google Sheets.
"""
import time
from fastapi import APIRouter, HTTPException

from src.api.schemas import UpdateCaseStagesRequest, UpdateCaseStagesResponse, SheetUpdateResult
from src.clients.sheets_client import read_range, write_single_cell, col_to_a1
from src.core import mycase_auto_session
from src.core import config
from src.core.exceptions import AuthenticationError, ScrapingError
from src.scraping.case_stages import (
    get_column_index,
    get_target_stage,
    update_case_stage,
    STATUS_COL_NAME,
    ID_COL_NAME,
    MYCASE_STATUS_COL_NAME,
    STATUS_PROCESADO,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/case-stages", tags=["Case Stages"])


@router.post("/run-batch", response_model=UpdateCaseStagesResponse)
def run_case_stage_batch(req: UpdateCaseStagesRequest) -> UpdateCaseStagesResponse:
    """
    Read all DAILY sheets, find rows where STATUS FULLY matches the stage map,
    skip rows already marked 'Procesado', and update Case Stage in MyCase.

    Writes 'Procesado' or 'Error al actualizar {stage}' to the
    'Actualización MyCase' column for each processed row.
    """
    started = time.time()
    spreadsheet_id = req.spreadsheet_id or config.CASE_STAGE_SPREADSHEET_ID
    sheets = req.sheets or config.CASE_STAGE_SHEETS

    response = UpdateCaseStagesResponse(ok=False, started_at=started, finished_at=started)

    try:
        with mycase_auto_session() as page:
            for sheet_name in sheets:
                sheet_result = SheetUpdateResult(sheet_name=sheet_name)
                logger.info("--- Procesando pestaña: %s ---", sheet_name)

                data = read_range(
                    sheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    range_notation="A:ZZ",
                )

                if not data or len(data) < 2:
                    logger.info("[%s] Sin datos o solo encabezado, omitiendo.", sheet_name)
                    response.sheets.append(sheet_result)
                    continue

                headers = data[0]
                status_idx = get_column_index(headers, STATUS_COL_NAME)
                id_idx = get_column_index(headers, ID_COL_NAME)
                mycase_idx = get_column_index(headers, MYCASE_STATUS_COL_NAME)

                if status_idx is None or id_idx is None:
                    logger.warning(
                        "[%s] Columnas '%s' o '%s' no encontradas.",
                        sheet_name, STATUS_COL_NAME, ID_COL_NAME,
                    )
                    response.sheets.append(sheet_result)
                    continue

                if mycase_idx is None:
                    logger.warning(
                        "[%s] Columna '%s' no encontrada, no se podrá escribir estado.",
                        sheet_name, MYCASE_STATUS_COL_NAME,
                    )
                    response.sheets.append(sheet_result)
                    continue

                mycase_col_a1 = col_to_a1(mycase_idx + 1)

                for i, row in enumerate(data):
                    if i == 0:
                        continue

                    # Pad row if shorter than expected columns
                    if len(row) <= max(status_idx, id_idx):
                        sheet_result.skipped += 1
                        continue

                    status_value = str(row[status_idx]).strip()
                    target_stage = get_target_stage(status_value)

                    if target_stage is None:
                        sheet_result.skipped += 1
                        continue

                    # Check Actualización MyCase — skip if already processed
                    mycase_current = (
                        str(row[mycase_idx]).strip()
                        if len(row) > mycase_idx
                        else ""
                    )
                    if mycase_current == STATUS_PROCESADO:
                        sheet_result.skipped += 1
                        continue

                    # i is 0-based index into data; sheet rows are 1-based → i + 1
                    sheet_row = i + 1
                    cell_a1 = f"{mycase_col_a1}{sheet_row}"

                    case_id_raw = str(row[id_idx]).strip()
                    try:
                        case_id = int(case_id_raw)
                    except ValueError:
                        logger.warning(
                            "[%s] ID inválido en fila %d: '%s', omitiendo.",
                            sheet_name, sheet_row, case_id_raw,
                        )
                        sheet_result.skipped += 1
                        continue

                    success = update_case_stage(page, case_id, target_stage)

                    if success:
                        write_single_cell(
                            sheet_id=spreadsheet_id,
                            sheet_name=sheet_name,
                            a1_range=cell_a1,
                            value=STATUS_PROCESADO,
                        )
                        sheet_result.ok += 1
                    else:
                        error_text = f"Error al actualizar {target_stage}"
                        write_single_cell(
                            sheet_id=spreadsheet_id,
                            sheet_name=sheet_name,
                            a1_range=cell_a1,
                            value=error_text,
                        )
                        logger.error("[%s] Fila %d → '%s'", sheet_name, sheet_row, error_text)
                        sheet_result.errors += 1

                logger.info(
                    "[%s] OK=%d | Errores=%d | Omitidas=%d",
                    sheet_name, sheet_result.ok, sheet_result.errors, sheet_result.skipped,
                )
                response.sheets.append(sheet_result)

        response.total_ok = sum(s.ok for s in response.sheets)
        response.total_errors = sum(s.errors for s in response.sheets)
        response.total_skipped = sum(s.skipped for s in response.sheets)
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
        logger.error("Authentication error en case-stages batch: %s", e)
        raise HTTPException(status_code=401, detail=str(e))

    except ScrapingError as e:
        response.error = str(e)
        response.finished_at = time.time()
        logger.error("Scraping error en case-stages batch: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        response.error = str(e)
        response.finished_at = time.time()
        logger.exception("Error inesperado en case-stages batch: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
