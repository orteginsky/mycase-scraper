# scripts/crear_buckets_gcs.py
"""
Crea los buckets de GCS necesarios para el proyecto (perfiles y artefactos)
si no existen todavía. Utiliza las credenciales de sa_key.json.
"""
import sys
import os
from pathlib import Path

# Añadir la raíz del proyecto al path para poder importar src
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core import config
from src.clients.gcs_client import GCSClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    print("=" * 60)
    print("  CREACIÓN DE BUCKETS EN GOOGLE CLOUD STORAGE")
    print("=" * 60)
    
    # Asegurar que usamos la cuenta de servicio local
    if os.path.exists("sa_key.json"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(Path("sa_key.json").resolve())
        print(f"🔑 Usando credenciales de: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")

    gcs = GCSClient()
    buckets_to_create = [
        config.PW_PROFILE_GCS_BUCKET,
        config.GCS_ARTIFACTS_BUCKET
    ]
    
    # Limpiar duplicados y vacíos
    buckets_to_create = list(set([b for b in buckets_to_create if b]))
    
    if not buckets_to_create:
        print("⚠ No hay buckets configurados en el .env (PW_PROFILE_GCS_BUCKET o GCS_ARTIFACTS_BUCKET)")
        return

    for b_name in buckets_to_create:
        try:
            print(f"\nVerificando bucket: {b_name}...")
            bucket = gcs.client.lookup_bucket(b_name)
            
            if bucket:
                print(f"✅ El bucket '{b_name}' ya existe.")
            else:
                print(f"➕ El bucket '{b_name}' no existe. Creando...")
                gcs.client.create_bucket(b_name, location=config.GCP_LOCATION)
                print(f"✨ Bucket '{b_name}' creado con éxito en {config.GCP_LOCATION}.")
                
        except Exception as e:
            print(f"❌ Error con el bucket '{b_name}': {e}")

if __name__ == "__main__":
    main()
