# scripts/actualizar_secreto_sesion.py
"""
Actualiza las cookies de sesión en Google Secret Manager.
Esto permite renovar la sesión en la nube sin volver a desplegar el código.
"""
import sys
import os
import subprocess
from pathlib import Path

# Añadir la raíz del proyecto al path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

SECRET_ID = "mycase_session_state"

def main():
    print("=" * 60)
    print("  ACTUALIZACIÓN DE SESIÓN EN SECRET MANAGER")
    print("=" * 60)

    # 1. Obtener la sesión actual desde la lógica de exportación
    try:
        from scripts.exportar_estado import get_state_base64
        # Intentamos buscar state.json local
        state_file = config.STATE_FILE
        if not state_file.exists():
            print(f"❌ ERROR: No se encontró el archivo de estado en {state_file}")
            print("Ejecuta primero 'python3 -m scripts.crear_sesion' para loguearte.")
            return

        print(f"Leyendo sesión desde: {state_file}")
        b64_data = get_state_base64(state_file)
        print(f"✅ Sesión codificada ({len(b64_data)} caracteres)")

    except Exception as e:
        print(f"❌ ERROR al procesar sesión local: {e}")
        return

    # 2. Subir a Secret Manager usando gcloud para evitar dependencias extra de Python
    project = config.GCP_PROJECT_ID or "ortega-473114"
    
    print(f"\nSubiendo al secreto '{SECRET_ID}' en el proyecto '{project}'...")
    
    # Verificar si el secreto existe
    check_cmd = ["gcloud", "secrets", "describe", SECRET_ID, "--project", project]
    exists = subprocess.run(check_cmd, capture_output=True).returncode == 0

    if not exists:
        print(f"➕ El secreto '{SECRET_ID}' no existe. Creándolo...")
        create_cmd = ["gcloud", "secrets", "create", SECRET_ID, "--replication-policy", "automatic", "--project", project]
        subprocess.run(create_cmd, check=True)

    # Añadir nueva versión
    add_version_cmd = ["gcloud", "secrets", "versions", "add", SECRET_ID, "--data-file=-", "--project", project]
    proc = subprocess.Popen(add_version_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(input=b64_data)

    if proc.returncode == 0:
        print("\n✅ ÉXITO: Secreto actualizado correctamente.")
        print("\n" + "="*60)
        print("  CONFIGURACIÓN FINAL EN CLOUD RUN")
        print("="*60)
        print("Copia y pega este comando para que Cloud Run use el secreto:")
        print(f"\ngcloud run services update mycase-scraper \\")
        print(f"  --update-secrets=PW_STATE_B64={SECRET_ID}:latest \\")
        print(f"  --set-env-vars=\"MYCASE_EMAIL={config.MYCASE_EMAIL},MYCASE_PASSWORD={config.MYCASE_PASSWORD}\" \\")
        print(f"  --project {project} --region us-central1")
        print("="*60)
    else:
        print(f"❌ ERROR al subir al Secret Manager: {stderr}")

if __name__ == "__main__":
    main()
