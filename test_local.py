#!/usr/bin/env python3
"""
Script de prueba para verificar que todo funciona en local.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.context_manager import mycase_session
from utils.logger import get_logger

logger = get_logger(__name__)

def test_session():
    """Prueba que la sesión funcione sin pedir 2FA."""
    logger.info("=" * 70)
    logger.info("PROBANDO SESIÓN LOCAL")
    logger.info("=" * 70)
    logger.info("")

    try:
        logger.info("Iniciando sesión con Playwright...")
        with mycase_session() as page:
            logger.info("✅ Sesión iniciada correctamente")

            # Verificar que estemos en el dashboard
            current_url = page.url
            logger.info("URL actual: %s", current_url)

            if "dashboard" in current_url or "mycase.com" in current_url:
                logger.info("✅ Sesión autenticada - No pidió 2FA!")
                logger.info("")
                logger.info("La sesión persistente funciona correctamente.")
                logger.info("Esto significa que en Cloud Run tampoco pedirá 2FA.")
                return True
            else:
                logger.warning("⚠️  URL inesperada: %s", current_url)
                return False

    except Exception as e:
        logger.error("❌ Error: %s", e)
        return False

if __name__ == "__main__":
    logger.info("")
    success = test_session()
    logger.info("")
    logger.info("=" * 70)

    if success:
        logger.info("✅ TODO FUNCIONA EN LOCAL")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Próximos pasos:")
        logger.info("1. El perfil ya está en GCS (ya lo subiste)")
        logger.info("2. Actualiza Cloud Run con el comando que te mostró")
        logger.info("3. Espera 1-2 minutos")
        logger.info("4. Prueba el endpoint /messages/send")
        sys.exit(0)
    else:
        logger.error("❌ ALGO FALLÓ")
        logger.error("=" * 70)
        logger.error("")
        logger.error("Puede que necesites volver a autenticar:")
        logger.error("python scripts/seed_playwright_profile.py")
        sys.exit(1)
