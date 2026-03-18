# src.app.py (o api/router.py)
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from api.schemas import DownloadPDFRequest, DownloadPDFResponse
from api.status_writer import write_status_if_requested
from utils.text_utils import sanitize_folder_name
from service_layer.mycase_play_service import login_mycase
from parsing_layer.mycase_documents import download_leads_pdfs, download_case_pdfs
from config.settings import DOWNLOAD_DIR
from config import settings
from clients.drive_client import upload_directory

app = FastAPI(title="MyCase Scraper – Download PDFs + Drive upload")

@app.post("/download-pdfs", response_model=DownloadPDFResponse)
def download_pdfs(req: DownloadPDFRequest):
    started = time.time()

    # Subcarpeta local
    safe_folder = sanitize_folder_name(req.client_name).strip() or f"case_{req.case_id}"
    target_dir = str(Path(DOWNLOAD_DIR) / safe_folder)

    # Estado inicial (opcional, Sheets)
    try:
        write_status_if_requested(
            sheet_id=req.sheet_id, row=req.row, col=req.col, value="RUNNING"
        )
    except Exception:
        pass

    p = context = page = None
    drive_info = None
    try:
        # Login
        p, context, page = login_mycase()

        # Descarga
        if req.kind == "lead":
            download_leads_pdfs(page, req.case_id, safe_folder)
        else:
            download_case_pdfs(page, req.case_id, safe_folder)

        # Subida a Drive (si hay carpeta default o la envían)
        parent_drive_folder = req.drive_folder_id or settings.DRIVE_DEFAULT_FOLDER_ID
        if parent_drive_folder:
            drive_info = upload_directory(
                parent_id=parent_drive_folder,
                local_dir=target_dir,
                create_subfolder=True,
                subfolder_name=safe_folder,  # carpeta por cliente dentro del parent
            )

        # Estado final OK
        try:
            write_status_if_requested(
                sheet_id=req.sheet_id, row=req.row, col=req.col, value="SUCCEEDED"
            )
        except Exception:
            pass

        finished = time.time()
        return DownloadPDFResponse(
            ok=True,
            kind=req.kind,
            case_id=req.case_id,
            subfolder=safe_folder,
            target_dir=target_dir,
            started_at=started,
            finished_at=finished,
            drive_parent_id=parent_drive_folder if parent_drive_folder else None,
            drive_target_folder_id=(drive_info or {}).get("target_folder_id") if drive_info else None,
            drive_files_count=(drive_info or {}).get("count") if drive_info else None,
            drive_files=(drive_info or {}).get("files") if drive_info else None,
        )

    except Exception as e:
        try:
            write_status_if_requested(
                sheet_id=req.sheet_id, row=req.row, col=req.col, value=f"FAILED: {type(e).__name__}"
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            if context:
                context.close()
            if p:
                p.stop()
        except Exception:
            pass
