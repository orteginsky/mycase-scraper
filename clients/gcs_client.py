# clients/gcs_client.py
from __future__ import annotations
from typing import Optional, Iterable, Dict, List, Tuple
import os
import mimetypes
import datetime as dt
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

from config import settings

# ===== Credenciales =====
def _get_storage_client() -> storage.Client:
    # Usa GOOGLE_APPLICATION_CREDENTIALS / SA_JSON como ya tienes en settings (mismo mecanismo que Sheets/Drive)
    # Si tu runtime ya está autenticado (Workload Identity / ADC), con storage.Client() basta.
    if settings.SA_JSON:
        import json
        info = json.loads(settings.SA_JSON)
        creds = service_account.Credentials.from_service_account_info(info)
        return storage.Client(credentials=creds)
    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        return storage.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)
    return storage.Client()  # ADC

# ===== Helpers de paths =====
def _norm_prefix(*parts: str) -> str:
    cleaned: List[str] = []
    for p in parts:
        if not p:
            continue
        p = p.replace("\\", "/").strip("/")
        if p:
            cleaned.append(p)
    return "/".join(cleaned)

def make_artifacts_prefix(
    *,
    kind: str,           # 'lead' | 'case'
    case_id: int | str,
    safe_client: str,
    when: Optional[dt.datetime] = None,
) -> str:
    """Crea un prefijo tipo: raw/YYYY/MM/{kind}/{case_id}/{safe_client}"""
    when = when or dt.datetime.utcnow()
    yyyy = when.strftime("%Y")
    mm = when.strftime("%m")
    return _norm_prefix("raw", yyyy, mm, str(kind), str(case_id), safe_client)

def to_gs_uri(bucket: str, blob_name: str) -> str:
    return f"gs://{bucket}/{blob_name}"

# ===== MIME =====
def _guess_content_type(path: str) -> str:
    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"

# ===== Subir un archivo =====
def upload_file(
    *,
    bucket_name: str,
    local_path: str,
    dest_blob: str,
    metadata: Optional[Dict[str, str]] = None,
    cache_control: str = "no-store",
) -> Dict:
    client = _get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_blob)
    blob.cache_control = cache_control
    if metadata:
        blob.metadata = metadata

    content_type = _guess_content_type(local_path)
    blob.upload_from_filename(local_path, content_type=content_type)

    return {
        "bucket": bucket_name,
        "blob": dest_blob,
        "gs_uri": to_gs_uri(bucket_name, dest_blob),
        "content_type": content_type,
        "size": os.path.getsize(local_path),
    }

# ===== Subir carpeta =====
def upload_directory(
    *,
    bucket_name: str,
    local_dir: str,
    dest_prefix: str,
    include_exts: Optional[Iterable[str]] = (".pdf", ".png", ".jpg", ".jpeg"),
    recursive: bool = False,
    metadata_fn: Optional[callable] = None,  # (local_path) -> dict
) -> Dict:
    """
    Sube archivos de 'local_dir' a 'gs://bucket_name/dest_prefix/...'.
    include_exts: lista de extensiones a incluir (None para incluir todo).
    metadata_fn: función que devuelve metadata por archivo (dict) o None.
    """
    client = _get_storage_client()
    bucket = client.bucket(bucket_name)

    local_dir = str(local_dir)
    base = Path(local_dir)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"No existe la carpeta local: {local_dir}")

    uploaded: List[Dict] = []
    pattern = "**/*" if recursive else "*"

    for entry in base.glob(pattern):
        if not entry.is_file():
            continue
        ext = entry.suffix.lower()
        if include_exts and ext not in set(e.lower() for e in include_exts):
            continue

        rel = entry.relative_to(base).as_posix()  # ruta relativa dentro del dir
        blob_name = _norm_prefix(dest_prefix, rel)
        blob = bucket.blob(blob_name)

        # Opcional: metadata por archivo
        mtd = metadata_fn(entry) if metadata_fn else None

        blob.cache_control = "no-store"
        if mtd:
            blob.metadata = mtd

        content_type = _guess_content_type(str(entry))
        blob.upload_from_filename(str(entry), content_type=content_type)

        uploaded.append({
            "bucket": bucket.name,
            "blob": blob_name,
            "gs_uri": to_gs_uri(str(bucket.name), blob_name),
            "content_type": content_type,
            "size": entry.stat().st_size,
        })

    return {
        "bucket": bucket_name,
        "prefix": dest_prefix,
        "count": len(uploaded),
        "files": uploaded,
    }

# ===== Signed URL =====
def sign_url(
    *,
    bucket_name: str,
    blob_name: str,
    expires_in_seconds: Optional[int] = None,
    method: str = "GET",
    content_type: Optional[str] = None,
) -> str:
    """
    Genera una URL firmada (v4). Requiere que el principal tenga permisos para firmar.
    """
    client = _get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    ttl = expires_in_seconds or settings.GCS_SIGNED_URL_TTL
    url = blob.generate_signed_url(
        version="v4",
        expiration=dt.timedelta(seconds=int(ttl)),
        method=method,
        content_type=content_type,
    )
    return url
