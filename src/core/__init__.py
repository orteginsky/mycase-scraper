# core/__init__.py
"""
Core module: configuration, credentials, exceptions, and context managers.

Quick-start:
    from src.core.context_manager import mycase_session, mycase_session_state
    from src.scraping import download_pdfs, extract_case_notes, send_text_message

    # Cookie/state-based session (recommended for Cloud Run):
    with mycase_session_state() as page:
        notes  = extract_case_notes(page, entity_id)
        result = download_pdfs(page, entity_id, "lead", "Client Name")
        msg    = send_text_message(page, case_id, "Hello!")

    # Persistent-profile session (local dev):
    with mycase_session() as page:
        result = download_pdfs(page, case_id, "case", "Client Name")
"""
from src.core.context_manager import (
    mycase_session,
    mycase_session_state,
    mycase_session_full,
    mycase_auto_session,
    load_state_path,
    check_session_active,
)

__all__ = [
    "mycase_session",
    "mycase_session_state",
    "mycase_session_full",
    "load_state_path",
    "check_session_active",
]
