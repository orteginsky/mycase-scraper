"""
Script: Descarga state.json desde GCS y verifica que la sesión de MyCase
sigue activa navegando al dashboard.

Requiere GCSClient disponible. Para verificar sin GCS usa validar_sesion.py.

Uso:
    python -m src.scripts.verificar_sesion
"""
from dotenv import load_dotenv

load_dotenv()

from src.core import config
from src.core.context_manager import _create_state_context, check_session_active

try:
    from src.clients.gcs_client import GCSClient  # type: ignore
    _GCS_AVAILABLE = True
except ImportError:
    _GCS_AVAILABLE = False


def main() -> None:
    state_file = str(config.STATE_FILE)
    state_remote = config.STATE_REMOTE

    # Download state from GCS
    if not _GCS_AVAILABLE:
        print("ERROR: GCSClient no disponible.")
        print("Usa `python -m src.scripts.validar_sesion` para verificar sin GCS.")
        return

    gcs = GCSClient()
    descargado = gcs.download_file(blob_name=state_remote, local_path=state_file)
    if not descargado:
        print(f"No se encontró {state_remote} en GCS.")
        print("Ejecuta primero: python -m src.scripts.crear_sesion")
        return

    print(f"Estado descargado desde GCS → {state_file}")

    # Verify session using context_manager helper
    p, browser, context, page = _create_state_context(state_file)
    try:
        page.goto(config.MYCASE_BASE_URL, timeout=30_000)
        active = check_session_active(page)
        url = page.url

        if active:
            print(f"Sesión VÁLIDA. URL actual: {url}")
        else:
            print(f"Sesión EXPIRADA o INVÁLIDA. URL actual: {url}")
            print("Vuelve a ejecutar: python -m src.scripts.crear_sesion")

        input("\nPulsa ENTER para cerrar el navegador... ")
    finally:
        context.close()
        browser.close()
        p.stop()


if __name__ == "__main__":
    main()
