# scraping/__init__.py
"""
Scraping module: MyCase data extraction and interaction logic.
"""
from scraping.documents import download_pdfs
from scraping.notes import extract_case_notes
from scraping.messaging import send_text_message

__all__ = ["download_pdfs", "extract_case_notes", "send_text_message"]
