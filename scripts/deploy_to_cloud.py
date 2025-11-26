#!/usr/bin/env python3
"""
Script completo para desplegar a Cloud Run con perfil autenticado.

Este script:
1. Verifica que existe un perfil autenticado localmente
2. Sube el perfil a GCS
3. Actualiza las variables de entorno en Cloud Run
4. Verifica el despliegue

Uso:
    python scripts/deploy_to_cloud.py
"""
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import config
from core.profile_sync import upload_profile_to_gcs
from utils.logger import get_logger

logger = get_logger(__name__)

# Configuración de Cloud Run
PROJECT_ID = "ortega-473114"
REGION = "us-central1"
SERVICE_NAME = "mycase-scraper-api"


def print_section(title):
    """Imprime una sección con formato."""
    logger.info("")
    logger.info("=" * 70)
    logger.info(title)
    logger.info("=" * 70)


def check_prerequisites():
    """Verifica que todo esté configurado correctamente."""
    print_section("Verificando prerequisitos")

    issues = []

    # Verificar credenciales de MyCase
    if not config.MYCASE_EMAIL:
        issues.append("MYCASE_EMAIL no está configurado en .env")
    else:
        logger.info("✓ MYCASE_EMAIL: %s", config.MYCASE_EMAIL)

    if not config.MYCASE_PASSWORD:
        issues.append("MYCASE_PASSWORD no está configurado en .env")
    else:
        logger.info("✓ MYCASE_PASSWORD: ********")

    # Verificar bucket GCS
    if not config.PW_PROFILE_GCS_BUCKET:
        issues.append("PW_PROFILE_GCS_BUCKET no está configurado en .env")
    else:
        logger.info("✓ GCS Bucket: %s", config.PW_PROFILE_GCS_BUCKET)

    # Verificar credenciales de Google
    if not config.GOOGLE_APPLICATION_CREDENTIALS:
        issues.append("GOOGLE_APPLICATION_CREDENTIALS no está configurado")
    elif not Path(config.GOOGLE_APPLICATION_CREDENTIALS).exists():
        issues.append(f"Archivo de credenciales no existe: {config.GOOGLE_APPLICATION_CREDENTIALS}")
    else:
        logger.info("✓ Google credentials: %s", config.GOOGLE_APPLICATION_CREDENTIALS)

    # Verificar perfil local
    if not config.PW_USER_DATA_DIR.exists():
        issues.append(f"Perfil no existe: {config.PW_USER_DATA_DIR}")
        issues.append("Ejecuta: python scripts/seed_playwright_profile.py")
    else:
        cookies_path = config.PW_USER_DATA_DIR / "Default" / "Network" / "Cookies"
        if not cookies_path.exists():
            issues.append("Perfil existe pero no tiene cookies guardadas")
            issues.append("Ejecuta: python scripts/seed_playwright_profile.py")
        else:
            logger.info("✓ Perfil autenticado existe: %s", config.PW_USER_DATA_DIR)
            logger.info("✓ Cookies: %s", cookies_path)

    if issues:
        logger.error("")
        logger.error("❌ Se encontraron problemas:")
        for issue in issues:
            logger.error("   - %s", issue)
        return False

    logger.info("")
    logger.info("✅ Todos los prerequisitos están listos")
    return True


def upload_profile():
    """Sube el perfil a GCS."""
    print_section("Subiendo perfil a GCS")

    logger.info("Bucket: gs://%s/%s", config.PW_PROFILE_GCS_BUCKET, config.PW_PROFILE_GCS_PREFIX)

    success = upload_profile_to_gcs()

    if success:
        logger.info("✅ Perfil subido exitosamente a GCS")
        return True
    else:
        logger.error("❌ Error al subir perfil a GCS")
        return False


def update_cloud_run_env():
    """Actualiza las variables de entorno en Cloud Run."""
    print_section("Actualizando variables de entorno en Cloud Run")

    env_vars = [
        f"MYCASE_EMAIL={config.MYCASE_EMAIL}",
        f"MYCASE_PASSWORD={config.MYCASE_PASSWORD}",
        f"PW_PROFILE_GCS_BUCKET={config.PW_PROFILE_GCS_BUCKET}",
        f"PW_PROFILE_GCS_PREFIX={config.PW_PROFILE_GCS_PREFIX}",
        "PW_HEADLESS=true",
        "PW_USER_DATA_DIR=/app/playwright_profile",
        "DOWNLOAD_DIR=/tmp/downloads",
    ]

    logger.info("Variables a configurar:")
    for var in env_vars:
        # Ocultar password en logs
        if "PASSWORD" in var:
            logger.info("   - MYCASE_PASSWORD=********")
        else:
            logger.info("   - %s", var)

    logger.info("")
    logger.info("Ejecutando: gcloud run services update...")

    cmd = [
        "gcloud", "run", "services", "update", SERVICE_NAME,
        "--region", REGION,
        "--project", PROJECT_ID,
        f"--set-env-vars={','.join(env_vars)}",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("✅ Variables de entorno actualizadas en Cloud Run")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("❌ Error al actualizar Cloud Run:")
        logger.error(e.stderr)
        return False
    except FileNotFoundError:
        logger.error("❌ gcloud no está instalado o no está en PATH")
        logger.error("Instala Google Cloud SDK: https://cloud.google.com/sdk/docs/install")
        return False


def configure_service_account():
    """Configura permisos de service account."""
    print_section("Configurando permisos de Service Account")

    logger.info("Obteniendo service account de Cloud Run...")

    # Obtener service account
    cmd = [
        "gcloud", "run", "services", "describe", SERVICE_NAME,
        "--region", REGION,
        "--project", PROJECT_ID,
        "--format=value(spec.template.spec.serviceAccount)"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        sa_email = result.stdout.strip()

        if not sa_email:
            sa_email = f"{PROJECT_ID}-compute@developer.gserviceaccount.com"
            logger.info("Usando service account por defecto: %s", sa_email)
        else:
            logger.info("Service account: %s", sa_email)

        # Otorgar permisos
        logger.info("Otorgando permisos al bucket...")

        cmd = [
            "gcloud", "storage", "buckets", "add-iam-policy-binding",
            f"gs://{config.PW_PROFILE_GCS_BUCKET}",
            f"--member=serviceAccount:{sa_email}",
            "--role=roles/storage.objectAdmin",
            "--project", PROJECT_ID,
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info("✅ Permisos configurados correctamente")
        return True

    except subprocess.CalledProcessError as e:
        logger.warning("⚠️  No se pudo configurar permisos automáticamente")
        logger.warning("Configúralos manualmente en Cloud Console")
        return False


def verify_deployment():
    """Verifica que el despliegue esté funcionando."""
    print_section("Verificando despliegue")

    # Obtener URL del servicio
    cmd = [
        "gcloud", "run", "services", "describe", SERVICE_NAME,
        "--region", REGION,
        "--project", PROJECT_ID,
        "--format=value(status.url)"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        service_url = result.stdout.strip()

        logger.info("URL del servicio: %s", service_url)
        logger.info("")
        logger.info("Endpoints disponibles:")
        logger.info("   - Health check: %s/health", service_url)
        logger.info("   - Config validation: %s/config/validate", service_url)
        logger.info("   - Send message: %s/messages/send", service_url)
        logger.info("")
        logger.info("Revisa los logs con:")
        logger.info("   gcloud run services logs read %s --region %s --limit 50", SERVICE_NAME, REGION)

        return True

    except subprocess.CalledProcessError:
        logger.error("❌ No se pudo obtener la URL del servicio")
        return False


def main():
    """Función principal."""
    logger.info("=" * 70)
    logger.info("DESPLIEGUE A CLOUD RUN CON PERFIL AUTENTICADO")
    logger.info("=" * 70)

    # Paso 1: Verificar prerequisitos
    if not check_prerequisites():
        logger.error("")
        logger.error("Por favor corrige los problemas antes de continuar")
        return 1

    # Paso 2: Subir perfil a GCS
    if not upload_profile():
        logger.error("")
        logger.error("No se pudo subir el perfil. Abortando.")
        return 1

    # Paso 3: Configurar service account
    configure_service_account()

    # Paso 4: Actualizar variables de entorno
    if not update_cloud_run_env():
        logger.error("")
        logger.error("No se pudieron actualizar las variables de entorno")
        return 1

    # Paso 5: Verificar despliegue
    verify_deployment()

    print_section("✅ DESPLIEGUE COMPLETADO")
    logger.info("")
    logger.info("El servicio ahora debería usar el perfil autenticado de GCS")
    logger.info("y NO debería pedir 2FA en cada request.")
    logger.info("")
    logger.info("Próximos pasos:")
    logger.info("1. Espera 1-2 minutos para que Cloud Run reinicie")
    logger.info("2. Revisa los logs para confirmar que el perfil se descargó")
    logger.info("3. Prueba enviando un mensaje de prueba")

    return 0


if __name__ == "__main__":
    sys.exit(main())
