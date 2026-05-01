# src/auth.py
from __future__ import annotations
import os
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

from functools import lru_cache
from typing import Iterable, Optional, Tuple

import google.auth
from google.auth.credentials import Credentials as BaseCredentials
from google.oauth2.service_account import Credentials as SACredentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

import vertexai

from src.core import config as settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# --- SCOPES GLOBALES ---
# --- SCOPES GLOBALES ---
DRIVE_SCOPES = ("https://www.googleapis.com/auth/drive.readonly",)
DOCS_SCOPES = ("https://www.googleapis.com/auth/documents",)
SHEETS_SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)

# 👇 AGREGAR ESTE
VERTEX_SCOPE = ("https://www.googleapis.com/auth/cloud-platform",)

# ✅ Fusión de todos los scopes
WORKSPACE_SCOPES = tuple(sorted(set(DRIVE_SCOPES + DOCS_SCOPES + SHEETS_SCOPES + VERTEX_SCOPE)))

# --- HELPERS ---
def _scopes_tuple(scopes: Optional[Iterable[str]]) -> Tuple[str, ...]:
    return tuple(sorted(set(scopes or [])))

def _from_service_account_file(path: str, scopes: Tuple[str, ...]) -> SACredentials:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró el archivo de credenciales: {path}")
    logger.debug(f"Usando Service Account JSON: {path}")
    return SACredentials.from_service_account_file(path, scopes=list(scopes))

def _adc_credentials(scopes: Tuple[str, ...]) -> BaseCredentials:
    creds, _ = google.auth.default(scopes=list(scopes))
    logger.debug("Usando credenciales Application Default Credentials (ADC).")
    return creds

# --- CREDENCIALES CACHEADAS ---
@lru_cache(maxsize=4)
def get_workspace_credentials(scopes: Optional[Iterable[str]] = WORKSPACE_SCOPES) -> BaseCredentials:
    scopes_t = _scopes_tuple(scopes)
    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        return _from_service_account_file(settings.GOOGLE_APPLICATION_CREDENTIALS, scopes_t)
    return _adc_credentials(scopes_t)

# --- CLIENTES GOOGLE API ---
@lru_cache(maxsize=4)
def build_drive_client():
    creds = get_workspace_credentials(WORKSPACE_SCOPES)
    logger.info("📁 Cliente Drive inicializado (cacheado).")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# src/auth.py
@lru_cache(maxsize=4)
def build_docs_client():
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    import certifi
    from googleapiclient.discovery import build

    creds = get_workspace_credentials(WORKSPACE_SCOPES)
    logger.info("📄 Cliente Docs inicializado (cacheado).")

    base_http = httplib2.Http(
        timeout=180,  # subimos a 180s
        ca_certs=certifi.where(),  # CA actualizadas
        disable_ssl_certificate_validation=False,
    )
    authed_http = AuthorizedHttp(creds, http=base_http)

    # NO mezclar credentials= con http=
    return build("docs", "v1", http=authed_http, cache_discovery=False)


@lru_cache(maxsize=4)
def build_sheets_client():
    creds = get_workspace_credentials(WORKSPACE_SCOPES)
    logger.info("📊 Cliente Sheets inicializado (cacheado).")
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

# --- VERTEX AI ---
@lru_cache(maxsize=1)
def init_vertex_ai() -> bool:
    """
    Inicializa Vertex AI con las mismas credenciales del entorno.
    Compatible con:
    - Cloud Run (ADC)
    - Local con SA JSON
    """
    project = settings.GCP_PROJECT_ID
    location = settings.GCP_LOCATION
    logger.info(f"🤖 Inicializando Vertex AI (proyecto={project}, región={location})...")

    try:
        # **Línea Clave:** Obtener las credenciales que ya funcionan para Drive/Docs/Sheets
        creds = get_workspace_credentials()
        # Refrescar el token (necesario si es un Service Account en local)
        creds.refresh(Request()) 
        
        # **Línea Clave:** Pasar las credenciales explícitamente a Vertex AI
        vertexai.init(project=project, location=location, credentials=creds)
        logger.info("✅ Vertex AI inicializado correctamente con credenciales explícitas.")
        # al final de init_vertex_ai
        from google.api_core.client_options import ClientOptions
        client_opts = ClientOptions(api_endpoint=f"{location}-aiplatform.googleapis.com")
        vertexai.init(project=project, location=location, credentials=creds) 
        return True

    except Exception as e:
        logger.error(f"Error al inicializar Vertex AI: {e}")
        # Es bueno relanzar el error para que el programa se detenga si la inicialización falla
        raise

def get_all_clients() -> dict:
    """Devuelve un paquete de clientes Google + Vertex listos para usar."""
    init_vertex_ai()
    return {
        "drive": build_drive_client(),
        "docs": build_docs_client(),
        "sheets": build_sheets_client(),
        "vertex_initialized": True,
    }
