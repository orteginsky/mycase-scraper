# tests/conftest.py
"""
Pytest configuration and fixtures for MyCase Scraper tests.
"""
import pytest
from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_pdf_request():
    """Sample request for PDF download endpoint."""
    return {
        "case_id": 12345,
        "client_name": "John Doe",
        "kind": "lead",
    }


@pytest.fixture
def sample_notes_request():
    """Sample request for notes extraction endpoint."""
    return {
        "case_id": 12345,
        "client_name": "John Doe",
        "kind": "case",
        "output_format": "markdown",
    }


@pytest.fixture
def sample_message_request():
    """Sample request for message send endpoint."""
    return {
        "case_id": 12345,
        "message": "Hello, this is a test message.",
        "client_name": "John Doe",
    }
