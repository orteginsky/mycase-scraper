# api/status_writer.py
"""
Utilities for writing task status to Google Sheets.
Handles status updates, result URLs, and error details.
"""
from typing import Optional, Any, List
from datetime import datetime

from src.clients.sheets_client import write_single_cell, get_sheets_service, col_to_a1
from src.core import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def write_status_if_requested(
    *,
    sheet_id: Optional[str],
    row: Optional[int],
    col: Optional[int],
    value: str,
    sheet_name: Optional[str] = None,
) -> bool:
    """
    Write a single value to a cell if sheet tracking is configured.

    Args:
        sheet_id: Google Sheet ID
        row: Row number (1-indexed)
        col: Column number (1-indexed)
        value: Value to write
        sheet_name: Sheet tab name (uses default if not provided)

    Returns:
        True if write was successful, False if skipped or failed
    """
    if not sheet_id or not row or not col:
        return False

    try:
        sheet_name = sheet_name or config.SHEET_DEFAULT_NAME
        a1 = f"{col_to_a1(int(col))}{int(row)}"
        write_single_cell(sheet_id=sheet_id, sheet_name=sheet_name, a1_range=a1, value=value)
        logger.debug("Wrote '%s' to %s!%s", value, sheet_name, a1)
        return True
    except Exception as e:
        logger.warning("Failed to write status to sheet: %s", e)
        return False


def update_task_status(
    *,
    sheet_id: Optional[str],
    row: Optional[int],
    status_col: Optional[int],
    status: str,
    result_col: Optional[int] = None,
    result_url: Optional[str] = None,
    timestamp_col: Optional[int] = None,
    error_col: Optional[int] = None,
    error_detail: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> bool:
    """
    Update multiple columns for a task in a single operation.

    Args:
        sheet_id: Google Sheet ID
        row: Row number (1-indexed)
        status_col: Column for status (RUNNING, SUCCEEDED, FAILED)
        status: Status value to write
        result_col: Optional column for result URL
        result_url: Optional URL to write in result column
        timestamp_col: Optional column for timestamp
        error_col: Optional column for error details
        error_detail: Optional error message
        sheet_name: Sheet tab name

    Returns:
        True if all writes successful, False otherwise
    """
    if not sheet_id or not row or not status_col:
        return False

    sheet_name = sheet_name or config.SHEET_DEFAULT_NAME
    success = True

    # Write status
    success &= write_status_if_requested(
        sheet_id=sheet_id, row=row, col=status_col, value=status, sheet_name=sheet_name
    )

    # Write result URL if provided
    if result_col and result_url:
        success &= write_status_if_requested(
            sheet_id=sheet_id, row=row, col=result_col, value=result_url, sheet_name=sheet_name
        )

    # Write timestamp if column provided
    if timestamp_col:
        timestamp = datetime.utcnow().isoformat() + "Z"
        success &= write_status_if_requested(
            sheet_id=sheet_id, row=row, col=timestamp_col, value=timestamp, sheet_name=sheet_name
        )

    # Write error detail if provided
    if error_col and error_detail:
        success &= write_status_if_requested(
            sheet_id=sheet_id, row=row, col=error_col, value=error_detail, sheet_name=sheet_name
        )

    return success


def write_batch_update(
    *,
    sheet_id: str,
    sheet_name: str,
    row: int,
    updates: List[tuple[int, Any]],
) -> bool:
    """
    Write multiple cell values in a single batch request.
    More efficient for multiple columns.

    Args:
        sheet_id: Google Sheet ID
        sheet_name: Sheet tab name
        row: Row number (1-indexed)
        updates: List of (column_number, value) tuples

    Returns:
        True if successful, False otherwise
    """
    if not updates:
        return True

    try:
        service = get_sheets_service()
        data = []

        for col, value in updates:
            a1 = f"{sheet_name}!{col_to_a1(col)}{row}"
            data.append({
                "range": a1,
                "values": [[value]],
            })

        body = {
            "valueInputOption": config.SHEETS_VALUE_INPUT_OPTION,
            "data": data,
        }

        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body=body,
        ).execute()

        logger.debug("Batch updated %d cells in row %d", len(updates), row)
        return True

    except Exception as e:
        logger.warning("Failed to batch update sheet: %s", e)
        return False


class TaskStatusTracker:
    """
    Helper class to track task status throughout its lifecycle.
    Automatically handles status updates to Google Sheets.
    """

    def __init__(
        self,
        sheet_id: Optional[str] = None,
        row: Optional[int] = None,
        status_col: Optional[int] = None,
        result_col: Optional[int] = None,
        timestamp_col: Optional[int] = None,
        error_col: Optional[int] = None,
        sheet_name: Optional[str] = None,
    ):
        self.sheet_id = sheet_id
        self.row = row
        self.status_col = status_col
        self.result_col = result_col or (status_col + 1 if status_col else None)
        self.timestamp_col = timestamp_col or (status_col + 2 if status_col else None)
        self.error_col = error_col
        self.sheet_name = sheet_name or config.SHEET_DEFAULT_NAME
        self._enabled = bool(sheet_id and row and status_col)

    def mark_running(self) -> bool:
        """Mark task as RUNNING."""
        if not self._enabled:
            return False
        return update_task_status(
            sheet_id=self.sheet_id,
            row=self.row,
            status_col=self.status_col,
            status="RUNNING",
            timestamp_col=self.timestamp_col,
            sheet_name=self.sheet_name,
        )

    def mark_succeeded(self, result_url: Optional[str] = None) -> bool:
        """Mark task as SUCCEEDED with optional result URL."""
        if not self._enabled:
            return False
        return update_task_status(
            sheet_id=self.sheet_id,
            row=self.row,
            status_col=self.status_col,
            status="SUCCEEDED",
            result_col=self.result_col,
            result_url=result_url,
            timestamp_col=self.timestamp_col,
            sheet_name=self.sheet_name,
        )

    def mark_failed(self, error: str, error_detail: Optional[str] = None) -> bool:
        """Mark task as FAILED with error info."""
        if not self._enabled:
            return False
        return update_task_status(
            sheet_id=self.sheet_id,
            row=self.row,
            status_col=self.status_col,
            status=f"FAILED: {error}",
            error_col=self.error_col,
            error_detail=error_detail,
            timestamp_col=self.timestamp_col,
            sheet_name=self.sheet_name,
        )
