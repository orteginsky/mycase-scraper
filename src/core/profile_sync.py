# core/profile_sync.py
"""
Playwright profile synchronization for Cloud Run.
Handles downloading/uploading browser profile to/from GCS for session persistence.
"""
from __future__ import annotations

import fnmatch
import io
import os
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import Iterable, Optional

from src.core import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Patrones que NO queremos persistir (pesado/inútil).
EXCLUDES = [
    "Cache/**",
    "Code Cache/**",
    "GPUCache/**",
    "ShaderCache/**",
    "GrShaderCache/**",
    "Service Worker/CacheStorage/**",
    "Extension State/**",
    "IndexedDB/**",
    "optimization_guide_model_store/**",
    "Segmentation Platform/**",
    "Media History/**",
]

# Si quieres limpiar el dir local antes de extraer el tar del GCS
CLEAN_BEFORE_EXTRACT = True


def _norm_prefix(p: str) -> str:
    if not p:
        return ""
    return p.rstrip("/")


def _should_exclude(rel_path: str, patterns: Iterable[str]) -> bool:
    rel_path = rel_path.replace("\\", "/")
    for pat in patterns:
        if fnmatch.fnmatch(rel_path, pat):
            return True
    return False


def _safe_extract_all(tar: tarfile.TarFile, path: Path) -> None:
    """
    Extract tar defensively to avoid path traversal.
    """
    base = path.resolve()
    for member in tar.getmembers():
        member_path = (path / member.name).resolve()
        if not str(member_path).startswith(str(base)):
            raise RuntimeError(f"Blocked unsafe path in tar: {member.name}")
    tar.extractall(path=path)


def _get_gcs_client():
    """Get Google Cloud Storage client, with or without explicit credentials."""
    try:
        from google.cloud import storage
        from src.core.credentials import get_gcs_credentials

        creds = None
        try:
            creds = get_gcs_credentials()
        except Exception:
            # Si no hay credenciales explícitas, ADC por defecto
            creds = None

        if creds is not None:
            return storage.Client(credentials=creds)
        return storage.Client()  # ADC
    except Exception as e:
        logger.error("Failed to create GCS client: %s", e)
        raise


def _archive_profile_dir(src_dir: Path, excludes: Iterable[str]) -> str:
    """
    Crea un .tar.gz temporal del perfil aplicando exclusiones.
    Devuelve la ruta del archivo temporal.
    """
    # Recolectar paths incluidos
    include_files = []
    for p in src_dir.rglob("*"):
        if p.is_dir():
            continue
        rel = str(p.relative_to(src_dir))
        if _should_exclude(rel, excludes):
            continue
        include_files.append((p, rel))

    # Crear tar.gz
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = tmp.name

    # compresión moderada para equilibrio (6)
    with tarfile.open(tmp_path, mode="w:gz", compresslevel=6) as tar:
        for abs_path, rel in include_files:
            tar.add(str(abs_path), arcname=rel)

    return tmp_path


def download_profile_from_gcs() -> bool:
    """
    Download Playwright browser profile from GCS.
    Used on Cloud Run startup to restore session cookies.

    Returns:
        True if profile was downloaded, False otherwise
    """
    bucket_name = (config.PW_PROFILE_GCS_BUCKET or "").strip()
    prefix = _norm_prefix(config.PW_PROFILE_GCS_PREFIX or "")
    if not bucket_name or not prefix:
        logger.debug("Profile sync disabled (no bucket/prefix configured)")
        return False

    archive_name = f"{prefix}/profile.tar.gz"

    try:
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(archive_name)

        from google.api_core import exceptions as gax
        try:
            # stream en memoria -> archivo temporal
            buf = io.BytesIO()
            blob.download_to_file(buf)  # levanta NotFound si no existe
            buf.seek(0)
        except gax.NotFound:
            logger.info("No profile archive found in GCS: %s/%s", bucket_name, archive_name)
            return False

        # Limpieza opcional para evitar mezclar perfiles
        if CLEAN_BEFORE_EXTRACT and config.PW_USER_DATA_DIR.exists():
            try:
                shutil.rmtree(config.PW_USER_DATA_DIR, ignore_errors=True)
            except Exception as e:
                logger.warning("Could not clean profile dir before extract: %s", e)

        config.PW_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            _safe_extract_all(tar, config.PW_USER_DATA_DIR)

        logger.info("Extracted profile to %s", config.PW_USER_DATA_DIR)
        return True

    except Exception as e:
        logger.error("Failed to download profile from GCS: %s", e)
        return False


def upload_profile_to_gcs() -> bool:
    """
    Upload Playwright browser profile to GCS.
    Should be called after successful login to persist session.

    Returns:
        True if profile was uploaded, False otherwise
    """
    bucket_name = (config.PW_PROFILE_GCS_BUCKET or "").strip()
    prefix = _norm_prefix(config.PW_PROFILE_GCS_PREFIX or "")
    if not bucket_name or not prefix:
        logger.debug("Profile sync disabled (no bucket/prefix configured)")
        return False

    if not config.PW_USER_DATA_DIR.exists():
        logger.warning("Profile directory does not exist: %s", config.PW_USER_DATA_DIR)
        return False

    archive_name = f"{prefix}/profile.tar.gz"
    tmp_object = f"{archive_name}.tmp"

    try:
        tmp_tar = _archive_profile_dir(config.PW_USER_DATA_DIR, EXCLUDES)

        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)

        # Subida atómica: primero a .tmp
        tmp_blob = bucket.blob(tmp_object)
        tmp_blob.upload_from_filename(tmp_tar, content_type="application/gzip")

        # Rename .tmp → final
        final_blob = bucket.blob(archive_name)
        # Si ya existe, mejor usar rewrite para clonar el contenido
        final_blob.rewrite(tmp_blob)
        # Borrar tmp
        tmp_blob.delete()

        os.unlink(tmp_tar)
        logger.info("Uploaded profile archive to GCS: %s/%s", bucket_name, archive_name)
        return True

    except Exception as e:
        logger.error("Failed to upload profile to GCS: %s", e)
        return False


def ensure_profile_available() -> bool:
    """
    Ensure Playwright profile is available.
    Downloads from GCS if not present locally.

    Returns:
        True if profile is available (local or downloaded), False otherwise
    """
    try:
        if config.PW_USER_DATA_DIR.exists() and any(config.PW_USER_DATA_DIR.iterdir()):
            logger.debug("Profile already exists locally")
            return True
    except Exception:
        # Si falla el listado (permiso/corrupción), intenta descargar
        pass

    return download_profile_from_gcs()


def sync_profile_after_login():
    """
    Sync profile to GCS after successful login.
    Call this after first login to persist the session for Cloud Run.
    """
    upload_profile_to_gcs()


class ProfileSyncMiddleware:
    """
    Context manager that ensures profile is synced before use
    and uploaded after successful operations.
    """

    def __enter__(self):
        ensure_profile_available()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Solo sube si no hubo excepción
        if exc_type is None:
            sync_profile_after_login()
        return False
