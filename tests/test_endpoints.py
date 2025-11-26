# tests/test_endpoints.py
"""
Tests for FastAPI endpoints.
These are integration tests that verify endpoint structure and validation.
Note: Most tests skip actual scraping to avoid external dependencies.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_root_endpoint(client):
    """Test root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_health_endpoint(client):
    """Test detailed health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "playwright_profile_exists" in data
    assert "google_credentials_configured" in data


def test_config_validate_endpoint(client):
    """Test configuration validation endpoint."""
    response = client.get("/config/validate")
    assert response.status_code == 200
    data = response.json()
    assert "scraping" in data
    assert "google" in data
    assert "all_valid" in data


def test_pdf_download_validation(client, sample_pdf_request):
    """Test PDF download request validation."""
    # Missing required field
    invalid_request = {"case_id": 12345}
    response = client.post("/pdfs/download", json=invalid_request)
    assert response.status_code == 422  # Validation error


def test_notes_extract_validation(client, sample_notes_request):
    """Test notes extraction request validation."""
    # Invalid output format
    invalid_request = {**sample_notes_request, "output_format": "invalid"}
    response = client.post("/notes/extract", json=invalid_request)
    assert response.status_code == 422


def test_message_send_validation(client, sample_message_request):
    """Test message send request validation."""
    # Empty message
    invalid_request = {"case_id": 12345, "message": ""}
    response = client.post("/messages/send", json=invalid_request)
    assert response.status_code == 422


def test_pdf_download_with_sheets_tracking(client):
    """Test PDF download with optional sheets tracking fields."""
    request = {
        "case_id": 12345,
        "client_name": "Test Client",
        "kind": "lead",
        "sheet_id": "1ABC123",
        "row": 5,
        "col": 4,
    }
    # This will fail due to auth, but validates the request structure
    with patch("api.endpoints.pdfs.mycase_session") as mock_session:
        mock_session.side_effect = Exception("Auth not configured for test")
        response = client.post("/pdfs/download", json=request)
        # Should fail with 500 (scraping error), not 422 (validation error)
        assert response.status_code == 500


def test_legacy_endpoint(client):
    """Test legacy /download-pdfs endpoint exists."""
    # Just verify the endpoint exists (will fail auth)
    with patch("api.endpoints.pdfs.mycase_session") as mock_session:
        mock_session.side_effect = Exception("Auth not configured for test")
        response = client.post(
            "/download-pdfs",
            json={"case_id": 12345, "client_name": "Test", "kind": "lead"},
        )
        # Should fail with 500 (not 404 for missing endpoint)
        assert response.status_code == 500


class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_pdf_request_defaults(self):
        """Test PDF request default values."""
        from api.schemas import DownloadPDFRequest

        req = DownloadPDFRequest(case_id=123, client_name="Test")
        assert req.kind == "lead"  # default
        assert req.sheet_id is None
        assert req.drive_folder_id is None

    def test_notes_request_defaults(self):
        """Test notes request default values."""
        from api.schemas import ExtractNotesRequest

        req = ExtractNotesRequest(case_id=123, client_name="Test")
        assert req.kind == "case"  # default
        assert req.output_format == "json"  # default
        assert req.save_to_gdoc is False

    def test_message_request_validation(self):
        """Test message request length validation."""
        from api.schemas import SendMessageRequest
        from pydantic import ValidationError

        # Should fail - message too long
        with pytest.raises(ValidationError):
            SendMessageRequest(case_id=123, message="x" * 1601)

    def test_drive_file_info(self):
        """Test DriveFileInfo model."""
        from api.schemas import DriveFileInfo

        info = DriveFileInfo(id="abc123", name="test.pdf")
        assert info.webViewLink is None  # optional

        info_with_link = DriveFileInfo(
            id="abc123", name="test.pdf", webViewLink="https://drive.google.com/file/..."
        )
        assert info_with_link.webViewLink is not None


class TestStatusWriter:
    """Test status writer utilities."""

    def test_col_to_a1_conversion(self):
        """Test column number to A1 notation conversion."""
        from utils.a1 import col_to_a1

        assert col_to_a1(1) == "A"
        assert col_to_a1(2) == "B"
        assert col_to_a1(26) == "Z"
        assert col_to_a1(27) == "AA"
        assert col_to_a1(52) == "AZ"

    def test_task_status_tracker_disabled(self):
        """Test tracker does nothing when not configured."""
        from api.status_writer import TaskStatusTracker

        tracker = TaskStatusTracker()  # no config
        assert tracker._enabled is False
        assert tracker.mark_running() is False
        assert tracker.mark_succeeded() is False
        assert tracker.mark_failed("error") is False


class TestExceptions:
    """Test custom exception classes."""

    def test_case_not_found_error(self):
        """Test CaseNotFoundError contains case_id."""
        from core.exceptions import CaseNotFoundError

        err = CaseNotFoundError(12345)
        assert err.case_id == 12345
        assert "12345" in str(err)

    def test_exception_hierarchy(self):
        """Test exception inheritance."""
        from core.exceptions import (
            MyCaseScraperError,
            AuthenticationError,
            ScrapingError,
            StorageError,
        )

        assert issubclass(AuthenticationError, MyCaseScraperError)
        assert issubclass(ScrapingError, MyCaseScraperError)
        assert issubclass(StorageError, MyCaseScraperError)
