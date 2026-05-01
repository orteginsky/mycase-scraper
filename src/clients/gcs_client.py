# clients/gcs_client.py
from __future__ import annotations
import os
import mimetypes
import datetime as dt
import json
from pathlib import Path
from typing import Optional, Iterable, Dict, List, Tuple

from google.cloud import storage
from google.oauth2 import service_account
from src.core import config as settings

class GCSClient:
    def __init__(self):
        self.client = self._get_storage_client()

    def _get_storage_client(self) -> storage.Client:
        """Inicializa el cliente oficial de Google Cloud Storage."""
        
        # 1. Caso: SA_JSON es el CONTENIDO del JSON (empieza con {)
        if settings.SA_JSON and settings.SA_JSON.strip().startswith("{"):
            try:
                info = json.loads(settings.SA_JSON)
                creds = service_account.Credentials.from_service_account_info(info)
                return storage.Client(credentials=creds)
            except json.JSONDecodeError as e:
                print("❌ Error al parsear el contenido de SA_JSON")
                raise e

        # 2. Caso: SA_JSON es una RUTA al archivo .json
        if settings.SA_JSON and os.path.isfile(settings.SA_JSON):
            return storage.Client.from_service_account_json(settings.SA_JSON)

        # 3. Caso: Usar la variable estándar de Google
        if settings.GOOGLE_APPLICATION_CREDENTIALS and os.path.isfile(settings.GOOGLE_APPLICATION_CREDENTIALS):
            return storage.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)

        # 4. Fallback: ADC (Application Default Credentials)
        return storage.Client()

    def _get_bucket(self, bucket_name: Optional[str] = None) -> storage.Bucket:
        name = bucket_name or settings.GCS_BUCKET_NAME
        return self.client.bucket(name)

    def exists(self, blob_name: str, bucket_name: Optional[str] = None) -> bool:
        """Verifica si un archivo existe en el bucket."""
        bucket = self._get_bucket(bucket_name)
        return bucket.blob(blob_name).exists()

    def upload_file(
        self,
        local_path: str | Path,
        dest_blob: str,
        bucket_name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        cache_control: str = "no-store",
    ) -> Dict:
        """Sube un archivo local al bucket."""
        bucket = self._get_bucket(bucket_name)
        blob = bucket.blob(dest_blob)
        blob.cache_control = cache_control
        if metadata:
            blob.metadata = metadata

        local_path_str = str(local_path)
        content_type, _ = mimetypes.guess_type(local_path_str)
        content_type = content_type or "application/octet-stream"
        
        blob.upload_from_filename(local_path_str, content_type=content_type)

        return {
            "bucket": bucket.name,
            "blob": dest_blob,
            "gs_uri": f"gs://{bucket.name}/{dest_blob}",
            "size": os.path.getsize(local_path_str),
        }

    def download_file(
        self,
        blob_name: str,
        local_path: str | Path,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Descarga un archivo del bucket a la ruta local."""
        try:
            bucket = self._get_bucket(bucket_name)
            blob = bucket.blob(blob_name)
            if not blob.exists():
                return False
            
            # Asegurar que el directorio local existe
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))
            return True
        except Exception:
            return False

    def sign_url(
        self,
        blob_name: str,
        bucket_name: Optional[str] = None,
        expires_in_seconds: Optional[int] = None,
        method: str = "GET"
    ) -> str:
        """Genera una URL firmada para acceso temporal."""
        bucket = self._get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        ttl = expires_in_seconds or getattr(settings, "GCS_SIGNED_URL_TTL", 3600)
        
        return blob.generate_signed_url(
            version="v4",
            expiration=dt.timedelta(seconds=int(ttl)),
            method=method
        )