# scripts/subir_perfil_gcs.py
"""
Sube el perfil de Playwright local (cookies y sesión) al bucket de GCS configurado.
Esto permite que la instancia en Cloud Run recupere la sesión al iniciar.
"""
import sys
import os
from pathlib import Path

# Añadir la raíz del proyecto al path para poder importar src
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core import config
from src.clients.gcs_client import GCSClient
from src.core.profile_sync import _archive_profile_dir, EXCLUDES
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    print("=" * 60)
    print("  SUBIDA DE PERFIL A GOOGLE CLOUD STORAGE")
    print("=" * 60)
    
    # Forzar uso de sa_key.json si existe localmente
    if os.path.exists("sa_key.json"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(Path("sa_key.json").resolve())
        print(f"🔑 Usando: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
    
    bucket_name = config.PW_PROFILE_GCS_BUCKET
    if not bucket_name:
        print("❌ ERROR: No hay PW_PROFILE_GCS_BUCKET configurado.")
        return

    gcs = GCSClient()
    prefix = config.PW_PROFILE_GCS_PREFIX.rstrip("/")
    archive_name = f"{prefix}/profile.tar.gz"
    
    if not config.PW_USER_DATA_DIR.exists():
        print(f"❌ ERROR: No existe {config.PW_USER_DATA_DIR}")
        return

    try:
        print(f"Comprimiendo perfil local ({config.PW_USER_DATA_DIR})...")
        tmp_tar = _archive_profile_dir(config.PW_USER_DATA_DIR, EXCLUDES)
        
        print(f"Subiendo a gs://{bucket_name}/{archive_name}...")
        gcs.upload_file(tmp_tar, archive_name, bucket_name=bucket_name)
        
        os.unlink(tmp_tar)
        print("\n✅ PERFIL SUBIDO CON ÉXITO.")
        
    except Exception as e:
        print(f"\n❌ FALLÓ LA SUBIDA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
