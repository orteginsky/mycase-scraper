# clients/sheets_client.py
"""
Google Sheets API client for reading and writing spreadsheet data.
"""
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build

from src.core.credentials import get_sheets_credentials
from src.core import config


def get_sheets_service():
    """Get authenticated Google Sheets service."""
    creds = get_sheets_credentials()
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def write_single_cell(
    *,
    sheet_id: str,
    sheet_name: str,
    a1_range: str,
    value: Any,
    value_input_option: Optional[str] = None,
) -> Dict:
    """
    Write a single value to a cell.

    Args:
        sheet_id: The spreadsheet ID
        sheet_name: The sheet/tab name
        a1_range: Cell address (e.g., "A1", "B5")
        value: Value to write
        value_input_option: RAW or USER_ENTERED (defaults to config setting)

    Returns:
        API response dict
    """
    service = get_sheets_service()
    value_input = value_input_option or config.SHEETS_VALUE_INPUT_OPTION

    body = {
        "range": f"{sheet_name}!{a1_range}",
        "majorDimension": "ROWS",
        "values": [[value]],
    }

    req = service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!{a1_range}",
        valueInputOption=value_input,
        body=body,
    )
    return req.execute()


def read_single_cell(
    *,
    sheet_id: str,
    sheet_name: str,
    a1_range: str,
) -> Any:
    """
    Read a single cell value.

    Args:
        sheet_id: The spreadsheet ID
        sheet_name: The sheet/tab name
        a1_range: Cell address (e.g., "A1", "B5")

    Returns:
        Cell value or None if empty
    """
    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!{a1_range}",
    ).execute()

    values = result.get("values", [])
    if values and values[0]:
        return values[0][0]
    return None


def read_range(
    *,
    sheet_id: str,
    sheet_name: str,
    range_notation: str,
) -> List[List[Any]]:
    """
    Read a range of cells.

    Args:
        sheet_id: The spreadsheet ID
        sheet_name: The sheet/tab name
        range_notation: Range (e.g., "A1:C10")

    Returns:
        2D list of values
    """
    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!{range_notation}",
    ).execute()

    return result.get("values", [])


def append_row(
    *,
    sheet_id: str,
    sheet_name: str,
    values: List[Any],
) -> Dict:
    """
    Append a row to the end of the sheet.

    Args:
        sheet_id: The spreadsheet ID
        sheet_name: The sheet/tab name
        values: List of values for the new row

    Returns:
        API response dict
    """
    service = get_sheets_service()
    body = {
        "values": [values],
    }

    return service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption=config.SHEETS_VALUE_INPUT_OPTION,
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()


def col_to_a1(col_num: int) -> str:
    """Convierte columna 1-based a letra A1 (1->A, 27->AA)."""
    if col_num < 1:
        raise ValueError("col debe ser >= 1")
    result = []
    n = col_num
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result.append(chr(65 + rem))
    return "".join(reversed(result))
