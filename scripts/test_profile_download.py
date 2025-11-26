#!/usr/bin/env python3
"""
Script para probar que el perfil de GCS se puede descargar correctamente.

Este script simula lo que hace Cloud Run al iniciar:
1. Descarga el perfil desde GCS
2. Verifica que contenga cookies válidas
3. Intenta usarlo para hacer login en MyCase

Esto te permite probar LOCALMENTE que todo funciona ANTES de desplegar a Cloud Run.

Uso:
    python scripts/test_profile_download.py
"""
import sys
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import config
from core.profile_sync import download_profile_from_gcs
from utils.logger import get_logger

logger = get_logger(__name__)


def backup_local_profile():
    """Hace backup del perfil local para poder restaurarlo después."""
    if config.PW_USER_DATA_DIR.exists():
        backup_dir = config.PW_USER_DATA_DIR.parent / f"{config.PW_USER_DATA_DIR.name}_backup"

        if backup_dir.exists():
            logger.info("Backup previo encontrado, eliminándolo...")
            shutil.rmtree(backup_dir)

        logger.info("Haciendo backup del perfil local...")
        shutil.copytree(config.PW_USER_DATA_DIR, backup_dir)
        logger.info("✓ Backup guardado en: %s", backup_dir)
        return backup_dir
    return None


def restore_local_profile(backup_dir):
    """Restaura el perfil local desde el backup."""
    if backup_dir and backup_dir.exists():
        logger.info("Restaurando perfil local desde backup...")

        if config.PW_USER_DATA_DIR.exists():
            shutil.rmtree(config.PW_USER_DATA_DIR)

        shutil.copytree(backup_dir, config.PW_USER_DATA_DIR)
        logger.info("✓ Perfil restaurado")

        # Limpiar backup
        shutil.rmtree(backup_dir)
        logger.info("✓ Backup eliminado")


def check_gcs_credentials():
    """Verifica que las credenciales de GCS estén configuradas."""
    logger.info("Verificando credenciales de GCS...")

    if config.GOOGLE_APPLICATION_CREDENTIALS:
        creds_path = Path(config.GOOGLE_APPLICATION_CREDENTIALS)
        if creds_path.exists():
            logger.info("✓ Credenciales: %s", creds_path)
            return True
        else:
            logger.error("❌ Archivo de credenciales no existe: %s", creds_path)
            return False
    else:
        logger.warning("⚠️  GOOGLE_APPLICATION_CREDENTIALS no configurado")
        logger.warning("   Intentando usar Application Default Credentials (ADC)")
        return True


def verify_profile_structure(profile_dir):
    """Verifica que el perfil tenga la estructura correcta."""
    logger.info("")
    logger.info("Verificando estructura del perfil...")

    checks = []

    # Buscar cookies en diferentes ubicaciones
    cookies_paths = [
        profile_dir / "Default" / "Network" / "Cookies",
        profile_dir / "Default" / "Cookies",
    ]

    cookies_found = False
    for cookies_path in cookies_paths:
        if cookies_path.exists():
            size = cookies_path.stat().st_size
            logger.info("✓ Cookies encontradas: %s (%d bytes)", cookies_path, size)
            cookies_found = True
            checks.append(True)
            break

    if not cookies_found:
        logger.error("❌ No se encontraron cookies")
        checks.append(False)

    # Verificar que no se descargaron archivos pesados
    cache_dirs = ["Cache", "Code Cache", "GPUCache", "ShaderCache"]
    for cache_dir in cache_dirs:
        cache_path = profile_dir / "Default" / cache_dir
        if cache_path.exists():
            logger.warning("⚠️  Carpeta de cache encontrada (no debería estar): %s", cache_dir)
        else:
            logger.info("✓ Cache excluida correctamente: %s", cache_dir)

    # Contar archivos totales
    total_files = sum(1 for _ in profile_dir.rglob("*") if _.is_file())
    total_size = sum(f.stat().st_size for f in profile_dir.rglob("*") if f.is_file())

    logger.info("")
    logger.info("Estadísticas del perfil:")
    logger.info("  - Archivos totales: %d", total_files)
    logger.info("  - Tamaño total: %.2f MB", total_size / 1024 / 1024)

    if total_size > 50 * 1024 * 1024:  # 50 MB
        logger.warning("⚠️  Perfil parece muy grande (>50MB)")
        logger.warning("   Puede incluir archivos cache innecesarios")

    return all(checks)


def test_login_with_profile():
    """Intenta hacer login usando el perfil descargado."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("PROBANDO LOGIN CON PERFIL DESCARGADO")
    logger.info("=" * 70)

    try:
        from service_layer.mycase_play_service import login_mycase

        logger.info("Iniciando sesión en MyCase...")
        logger.info("(Esto puede tardar 10-30 segundos)")
        logger.info("")

        p, context, page = login_mycase()

        # Verificar URL actual
        current_url = page.url
        logger.info("URL actual: %s", current_url)

        # Verificar si estamos en el dashboard (login exitoso)
        if "dashboard" in current_url or "mycase.com" in current_url:
            # Verificar que NO estemos en la página de login
            if "login" in current_url or "auth.mycase.com" in current_url:
                logger.error("❌ Estamos en la página de login - perfil NO funcionó")
                logger.error("   Las cookies pueden haber expirado")
                success = False
            else:
                logger.info("✅ Login exitoso sin 2FA")
                logger.info("   Perfil autenticado funcionando correctamente")
                success = True
        else:
            logger.error("❌ URL inesperada - puede requerir 2FA")
            success = False

        # Cerrar navegador
        logger.info("")
        logger.info("Cerrando navegador...")
        try:
            context.close()
            p.stop()
        except Exception:
            pass

        return success

    except Exception as e:
        logger.error("❌ Error durante el login: %s", e)
        logger.exception("Detalles del error:")
        return False


def main():
    """Función principal."""
    logger.info("=" * 70)
    logger.info("TEST: DESCARGA Y VALIDACIÓN DE PERFIL DESDE GCS")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Este script simula lo que hace Cloud Run:")
    logger.info("1. Descarga el perfil desde GCS")
    logger.info("2. Verifica que contenga cookies válidas")
    logger.info("3. Intenta hacer login (sin 2FA)")
    logger.info("")
    logger.info("NOTA: Tu perfil local será respaldado y restaurado después")
    logger.info("=" * 70)
    logger.info("")

    # Verificar credenciales
    if not check_gcs_credentials():
        logger.error("")
        logger.error("Configura GOOGLE_APPLICATION_CREDENTIALS en .env")
        return 1

    # Verificar configuración GCS
    if not config.PW_PROFILE_GCS_BUCKET:
        logger.error("")
        logger.error("PW_PROFILE_GCS_BUCKET no está configurado en .env")
        return 1

    logger.info("")
    logger.info("Configuración:")
    logger.info("  - GCS Bucket: %s", config.PW_PROFILE_GCS_BUCKET)
    logger.info("  - GCS Prefix: %s", config.PW_PROFILE_GCS_PREFIX)
    logger.info("  - Perfil local: %s", config.PW_USER_DATA_DIR)
    logger.info("")

    # Hacer backup del perfil local
    backup_dir = backup_local_profile()

    try:
        # Limpiar perfil local para simular Cloud Run
        if config.PW_USER_DATA_DIR.exists():
            logger.info("Limpiando perfil local para simular ambiente de Cloud Run...")
            shutil.rmtree(config.PW_USER_DATA_DIR)
            logger.info("✓ Perfil local eliminado")

        logger.info("")
        logger.info("=" * 70)
        logger.info("PASO 1: Descargando perfil desde GCS")
        logger.info("=" * 70)

        # Descargar perfil desde GCS
        success = download_profile_from_gcs()

        if not success:
            logger.error("")
            logger.error("❌ No se pudo descargar el perfil desde GCS")
            logger.error("")
            logger.error("Posibles causas:")
            logger.error("  1. El perfil no existe en GCS")
            logger.error("     Ejecuta: python scripts/upload_profile_to_gcs.py")
            logger.error("")
            logger.error("  2. Credenciales sin permisos")
            logger.error("     Verifica roles en service account:")
            logger.error("     - roles/storage.objectViewer")
            logger.error("")
            logger.error("  3. Bucket incorrecto")
            logger.error("     Verifica PW_PROFILE_GCS_BUCKET en .env")
            return 1

        logger.info("✅ Perfil descargado exitosamente desde GCS")

        # Verificar estructura
        logger.info("")
        logger.info("=" * 70)
        logger.info("PASO 2: Verificando estructura del perfil")
        logger.info("=" * 70)

        structure_ok = verify_profile_structure(config.PW_USER_DATA_DIR)

        if not structure_ok:
            logger.error("")
            logger.error("❌ La estructura del perfil no es válida")
            logger.error("   Re-crea el perfil: python scripts/seed_playwright_profile.py")
            return 1

        logger.info("✅ Estructura del perfil válida")

        # Probar login
        logger.info("")
        login_ok = test_login_with_profile()

        # Resumen
        logger.info("")
        logger.info("=" * 70)
        logger.info("RESUMEN")
        logger.info("=" * 70)
        logger.info("  Descarga desde GCS:     ✅ OK")
        logger.info("  Estructura del perfil:  %s", "✅ OK" if structure_ok else "❌ FALLO")
        logger.info("  Login sin 2FA:          %s", "✅ OK" if login_ok else "❌ FALLO")
        logger.info("")

        if login_ok:
            logger.info("✅ TODO LISTO PARA CLOUD RUN")
            logger.info("")
            logger.info("El perfil funciona correctamente.")
            logger.info("Puedes desplegar a Cloud Run con confianza:")
            logger.info("  python scripts/deploy_to_cloud.py")
            logger.info("")
            logger.info("O desplegar manualmente:")
            logger.info("  gcloud run deploy mycase-scraper-api \\")
            logger.info("    --source . \\")
            logger.info("    --region us-central1 \\")
            logger.info("    --set-env-vars=\"PW_PROFILE_GCS_BUCKET=%s\"", config.PW_PROFILE_GCS_BUCKET)
            return 0
        else:
            logger.error("❌ EL PERFIL NO FUNCIONA")
            logger.error("")
            logger.error("El perfil se descargó pero el login falló.")
            logger.error("Las cookies pueden haber expirado.")
            logger.error("")
            logger.error("Pasos de corrección:")
            logger.error("  1. Re-crea el perfil autenticado:")
            logger.error("     python scripts/seed_playwright_profile.py")
            logger.error("")
            logger.error("  2. Sube el nuevo perfil a GCS:")
            logger.error("     python scripts/upload_profile_to_gcs.py")
            logger.error("")
            logger.error("  3. Ejecuta este test de nuevo:")
            logger.error("     python scripts/test_profile_download.py")
            return 1

    finally:
        # Restaurar perfil local
        logger.info("")
        logger.info("=" * 70)
        logger.info("LIMPIEZA")
        logger.info("=" * 70)

        if backup_dir:
            restore_local_profile(backup_dir)
            logger.info("✅ Perfil local restaurado")

        logger.info("")


if __name__ == "__main__":
    sys.exit(main())
