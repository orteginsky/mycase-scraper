# ============================================
# data_layer/playwright_driver.py
# ============================================
import base64
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from config.settings import (
    PW_BLOCK_RESOURCES,
    PW_HEADLESS,
    PW_TIMEOUT_MS,
    PW_USER_DATA_DIR,
)
from utils.logger import get_logger

logger = get_logger(__name__)

BROWSER_CHANNEL = os.getenv("PW_BROWSER_CHANNEL", "").strip()

_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
]


def _state_file_from_env() -> str | None:
    """
    Si PW_STATE_B64 está definida, decodifica el base64 y escribe el JSON en
    un archivo temporal. Devuelve la ruta al archivo; None si no hay variable.
    """
    raw = os.getenv("PW_STATE_B64", "").strip()
    if not raw:
        return None

    try:
        decoded = base64.b64decode(raw)
        json.loads(decoded)  # validar que es JSON válido
    except Exception as e:
        logger.error("PW_STATE_B64 inválida: %s", e)
        return None

    tmp = tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="wb", prefix="pw_state_"
    )
    tmp.write(decoded)
    tmp.close()
    logger.info("Estado de sesión restaurado desde PW_STATE_B64 → %s", tmp.name)
    return tmp.name


def create_playwright_context(persistent: bool = True):
    """
    Crea un contexto de Playwright optimizado para scraping MyCase.

    Prioridad de sesión:
      1. PW_STATE_B64 (env var con base64 del state.json) → context efímero con storage_state
      2. Perfil persistente en disco (PW_USER_DATA_DIR)   → launch_persistent_context

    Returns:
        tuple: (p, context, page)
    """
    p = sync_playwright().start()

    try:
        launch_kwargs = {
            "headless": PW_HEADLESS,
            "args": _LAUNCH_ARGS,
        }
        if BROWSER_CHANNEL:
            launch_kwargs["channel"] = BROWSER_CHANNEL

        state_file = _state_file_from_env()

        if state_file:
            # --- Modo Docker / variable de entorno ---
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(storage_state=state_file)
            logger.info("Contexto creado desde PW_STATE_B64 (headless=%s)", PW_HEADLESS)

        elif persistent:
            # --- Modo local con perfil persistente en disco ---
            user_data_dir = Path(PW_USER_DATA_DIR)
            user_data_dir.mkdir(parents=True, exist_ok=True)
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                **launch_kwargs,
            )
            logger.info(
                "Contexto persistente creado en %s | channel=%s",
                user_data_dir,
                BROWSER_CHANNEL or "<default chromium>",
            )

        else:
            # --- Contexto efímero sin sesión ---
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context()
            logger.info("Contexto efímero iniciado.")

        page = context.new_page()
        page.set_default_timeout(PW_TIMEOUT_MS)

        if PW_BLOCK_RESOURCES:
            page.route(
                "**/*",
                lambda route, req: (
                    route.abort()
                    if req.resource_type in PW_BLOCK_RESOURCES
                    else route.continue_()
                ),
            )

        logger.info("Playwright listo (headless=%s)", PW_HEADLESS)
        return p, context, page

    except Exception as e:
        logger.exception("Error creando el contexto de Playwright: %s", e)
        raise
