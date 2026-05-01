# clients/drive_client.py
"""
Google Drive API client for uploading files and managing folders.
"""
from __future__ import annotations
from typing import Optional, List, Dict
import mimetypes

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.core.credentials import get_drive_credentials
from src.core import config


def get_drive_service():
    """Get authenticated Google Drive service."""
    creds = get_drive_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def _is_pdf(path: str) -> bool:
    mt, _ = mimetypes.guess_type(path)
    return (mt == "application/pdf") or path.lower().endswith(".pdf")

def ensure_subfolder(parent_id: str, name: str) -> str:
    """
    Ensure a subfolder exists in Drive. Creates if not found.

    Args:
        parent_id: Parent folder ID
        name: Subfolder name

    Returns:
        Subfolder ID
    """
    svc = get_drive_service()

    # Escape single quotes for Drive query
    escaped_name = name.replace("'", "\\'")

    q = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{escaped_name}' "
        f"and '{parent_id}' in parents and trashed=false"
    )

    res = svc.files().list(
        q=q,
        spaces="drive",
        fields="files(id,name)",
        includeItemsFromAllDrives=config.DRIVE_USE_SHARED_DRIVE,
        supportsAllDrives=config.DRIVE_USE_SHARED_DRIVE,
        pageSize=1,
    ).execute()

    files = res.get("files", [])
    if files:
        return files[0]["id"]

    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    created = svc.files().create(
        body=file_metadata,
        fields="id",
        supportsAllDrives=config.DRIVE_USE_SHARED_DRIVE,
    ).execute()
    return created["id"]

def upload_file(parent_id: str, local_path: str) -> Dict:
    """
    Upload a PDF file to Drive.

    Args:
        parent_id: Destination folder ID
        local_path: Local file path

    Returns:
        Dict with id, name, webViewLink
    """
    if not _is_pdf(local_path):
        raise ValueError(f"Not a PDF: {local_path}")

    svc = get_drive_service()
    media = MediaFileUpload(local_path, mimetype="application/pdf", resumable=False)
    metadata = {"name": local_path.split("/")[-1].split("\\")[-1], "parents": [parent_id]}

    created = svc.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,webViewLink",
        supportsAllDrives=config.DRIVE_USE_SHARED_DRIVE,
    ).execute()
    return created

def upload_directory(
    *,
    parent_id: str,
    local_dir: str,
    create_subfolder: bool = True,
    subfolder_name: Optional[str] = None,
) -> Dict:
    """
    Sube todos los PDFs de 'local_dir' a Drive. Si create_subfolder=True,
    crea una subcarpeta 'subfolder_name' bajo parent_id y sube allí.
    Devuelve {parent_id, target_folder_id, files:[{id,name,webViewLink}], count}.
    """
    import os
    files_uploaded: List[Dict] = []

    target_folder_id = parent_id
    if create_subfolder:
        name = subfolder_name or local_dir.split("/")[-1].split("\\")[-1]
        target_folder_id = ensure_subfolder(parent_id, name)

    for entry in os.scandir(local_dir):
        if entry.is_file() and _is_pdf(entry.path):
            info = upload_file(target_folder_id, entry.path)
            files_uploaded.append(info)

    return {
        "parent_id": parent_id,
        "target_folder_id": target_folder_id,
        "files": files_uploaded,
        "count": len(files_uploaded),
    }
