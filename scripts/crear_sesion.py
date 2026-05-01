"""
Script 1/3: Abre el navegador para login manual con 2FA.
Una vez en el dashboard, guarda cookies/estado en state.json
y opcionalmente lo sube a GCS.

Uso:
    python -m src.scripts.crear_sesion

Siguiente paso:
    python -m src.scripts.exportar_estado   # codifica a PW_STATE_B64
    python -m src.scripts.validar_sesion    # verifica que sea válido
"""
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

from src.core import config

# GCS upload is optional — skip gracefully if client is unavailable
try:
    from src.clients.gcs_client import GCSClient  # type: ignore
    _GCS_AVAILABLE = True
except ImportError:
    _GCS_AVAILABLE = False


def main() -> None:
    state_file = str(config.STATE_FILE)
    state_remote = config.STATE_REMOTE

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(config.MYCASE_BASE_URL)
        page.bring_to_front()

        print("=" * 55)
        print("  Completa el login y el código 2FA en el navegador.")
        print("  Cuando veas el DASHBOARD, regresa aquí y pulsa ENTER.")
        print("=" * 55)
        input("\n>>> ")

        # Save cookies + localStorage to state.json
        context.storage_state(path=state_file)
        print(f"Estado guardado localmente en: {state_file}")

        # Upload to GCS if available
        if _GCS_AVAILABLE:
            try:
                gcs = GCSClient()
                gcs.upload_file(local_path=state_file, dest_blob=state_remote)
                print(f"Estado subido a GCS en: {state_remote}")
            except Exception as e:
                print(f"AVISO: No se pudo subir a GCS: {e}")
        else:
            print("AVISO: GCSClient no disponible — estado guardado solo localmente.")

        browser.close()

    print()
    print("Siguiente paso:")
    print("  python -m src.scripts.exportar_estado   # genera PW_STATE_B64")
    print("  python -m src.scripts.validar_sesion    # verifica la sesión")


if __name__ == "__main__":
    main()
