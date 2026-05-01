# scraping/__init__.py
"""
Scraping module: MyCase data extraction and interaction logic.

All scraping functions accept a Playwright ``page`` object.
Use a context manager from ``core`` to obtain a ready-to-use page:

    from src.core import mycase_session, mycase_session_state
    from src.scraping import download_pdfs, extract_case_notes, send_text_message

    with mycase_session_state() as page:
        result = extract_case_notes(page, entity_id)
        notes  = result["notes"]
        docs   = download_pdfs(page, entity_id, "lead", "Client Name")
        result = send_text_message(page, case_id, "Hello!")
"""
from src.scraping.documents import download_pdfs
from src.scraping.notes import extract_case_notes, extract_case_details
from src.scraping.messages import send_text_message, verify_message_sent
from src.scraping.cases import get_case_name

__all__ = [
    "download_pdfs",
    "extract_case_notes",
    "extract_case_details",
    "send_text_message",
    "verify_message_sent",
    "get_case_name",
]
