# scripts/validar_perfil_gcs.py
"""
Valida que el perfil de Playwright exista en el bucket de GCS y sea accesible.
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Añadir la raíz del proyecto al path para poder importar src
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core import config
from src.clients.gcs_client import GCSClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    print("=" * 60)
    print("  VALIDACIÓN DE PERFIL EN GOOGLE CLOUD STORAGE")
    print("=" * 60)
    
    # Forzar uso de sa_key.json si existe localmente
    if os.path.exists("sa_key.json"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(Path("sa_key.json").resolve())
        print(f"🔑 Usando: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")

    bucket_name = config.PW_PROFILE_GCS_BUCKET
    prefix = config.PW_PROFILE_GCS_PREFIX.rstrip("/")
    archive_name = f"{prefix}/profile.tar.gz"
    
    if not bucket_name:
        print("❌ ERROR: PW_PROFILE_GCS_BUCKET no está configurado.")
        return

    try:
        gcs = GCSClient()
        bucket = gcs.client.bucket(bucket_name)
        blob = bucket.blob(archive_name)
        
        if blob.exists():
            blob.reload()
            size_mb = blob.size / (1024 * 1024)
            updated = blob.updated
            
            print(f"\n✅ RECURSO ENCONTRADO")
            print(f"Bucket      : {bucket_name}")
            print(f"Archivo     : {archive_name}")
            print(f"Tamaño      : {size_mb:.2f} MB")
            print(f"Actualizado : {updated} (UTC)")
            # Verificación básica de antigüedad
            now = datetime.now(updated.tzinfo)
            age_days = (now - updated).days
            if age_days > 7:
                print(f"⚠  ADVERTENCIA: El perfil tiene {age_days} días. Podría estar expirado.")
            else:
                print(f"✨ El perfil es reciente ({age_days} días).")
        else:
            print(f"\n❌ ERROR: El archivo gs://{bucket_name}/{archive_name} NO existe.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
