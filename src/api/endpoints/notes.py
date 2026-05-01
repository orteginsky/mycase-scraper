# api/endpoints/notes.py
"""
Endpoint for extracting notes from MyCase.
"""
import time
import json
from typing import List
from fastapi import APIRouter, HTTPException

from src.api.schemas import ExtractNotesRequest, ExtractNotesResponse, NoteItem
from src.api.status_writer import TaskStatusTracker
from src.core import mycase_auto_session
from src.core import config
from src.core.exceptions import CaseNotFoundError, ScrapingError, AuthenticationError
from src.scraping.notes import extract_case_notes
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/notes", tags=["Notes"])


def _format_notes_as_text(notes: List[dict], case_name: str = None) -> str:
    """Format notes as plain text."""
    lines = []
    if case_name:
        lines.append(f"Case: {case_name}")
        lines.append("=" * 50)
        lines.append("")

    for i, note in enumerate(notes, 1):
        lines.append(f"Note #{i}")
        if note.get("id"):
            lines.append(f"ID: {note['id']}")
        if note.get("subject"):
            lines.append(f"Subject: {note['subject']}")
        if note.get("author"):
            lines.append(f"Author: {note['author']}")
        if note.get("date"):
            lines.append(f"Date: {note['date']}")
        lines.append("-" * 30)
        lines.append(note.get("body", ""))
        lines.append("")

    return "\n".join(lines)


def _format_notes_as_markdown(notes: List[dict], case_name: str = None) -> str:
    """Format notes as Markdown."""
    lines = []
    if case_name:
        lines.append(f"# {case_name}")
        lines.append("")

    for i, note in enumerate(notes, 1):
        lines.append(f"## Note #{i}")
        if note.get("id"):
            lines.append(f"*   **ID:** `{note['id']}`")
        if note.get("subject"):
            lines.append(f"*   **Subject:** {note['subject']}")
        
        metadata = []
        if note.get("author"):
            metadata.append(f"**Author:** {note['author']}")
        if note.get("date"):
            metadata.append(f"**Date:** {note['date']}")
        if metadata:
            lines.append("*   " + " | ".join(metadata))
            lines.append("")
        
        lines.append(note.get("body", ""))
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


@router.post("/extract", response_model=ExtractNotesResponse)
def extract_notes_endpoint(req: ExtractNotesRequest) -> ExtractNotesResponse:
    """
    Extract notes and metadata from a MyCase case or lead.

    This endpoint:
    1. Logs into MyCase (uses persistent session)
    2. Navigates to the notes section
    3. Extracts case metadata and all notes
    4. Formats output as JSON, text, or markdown
    5. Optionally saves to Google Doc or GCS
    6. Updates status in Google Sheets (if configured)

    Returns:
        ExtractNotesResponse with notes data and metadata
    """
    started = time.time()

    # Setup status tracker
    tracker = TaskStatusTracker(
        sheet_id=req.sheet_id,
        row=req.row,
        status_col=req.col,
    )

    # Prepare response
    response = ExtractNotesResponse(
        ok=False,
        case_id=req.case_id,
        client_name=req.client_name,
        kind=req.kind,
        started_at=started,
        finished_at=started,
        output_format=req.output_format,
        type=req.type,
    )

    # Mark as running
    tracker.mark_running()

    try:
        # Extract notes using context manager
        with mycase_auto_session() as page:
            logger.info("Extracting notes for %s %d (%s)", req.kind, req.case_id, req.client_name or "N/A")

            result = extract_case_notes(
                page=page,
                entity_id=req.case_id,
                entity_type=req.kind,
                type=req.type,
            )

            notes_list = result["notes"]
            response.type = result.get("type")
            
            # En la nueva lógica ya no extraemos metadatos por separado aquí, 
            # pero podríamos si fuera necesario. Por ahora usamos lo que retorna el parser.
            response.notes = [NoteItem(**n) for n in notes_list]
            response.notes_count = len(response.notes)

        # Format notes based on requested output
        if req.output_format == "text":
            response.notes_text = _format_notes_as_text(
                [n.model_dump() for n in response.notes],
                response.case_name,
            )
        elif req.output_format == "markdown":
            response.notes_text = _format_notes_as_markdown(
                [n.model_dump() for n in response.notes],
                response.case_name,
            )

        # TODO: Save to Google Doc if requested
        # TODO: Save to GCS if configured

        # Mark success
        response.ok = True
        response.finished_at = time.time()
        tracker.mark_succeeded()

        logger.info(
            "Extracted %d notes in %.2fs",
            response.notes_count,
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
        logger.exception("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
