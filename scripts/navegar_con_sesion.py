import sys
from pathlib import Path

# Load project root and add to sys.path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(_ROOT))

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=_ROOT / ".env")

from src.core import config
from src.core.context_manager import load_state_path
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main() -> None:
    # 1. Obtener la ruta del estado (cookies)
    state_path = load_state_path()
    
    if not state_path:
        print("ERROR: No se encontró un archivo de estado (state.json) ni la variable PW_STATE_B64.")
        print("Por favor, ejecuta 'python scripts/crear_sesion.py' primero para generar la sesión.")
        return

    print(f"Cargando sesión desde: {state_path}")
    
    with sync_playwright() as p:
        # Lanzar navegador con interfaz gráfica
        browser = p.chromium.launch(headless=False)
        
        # Crear contexto cargando el estado guardado
        context = browser.new_context(
            storage_state=state_path,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        # Ir a la URL base de MyCase
        print(f"Navegando a: {config.MYCASE_BASE_URL}")
        page.goto(config.MYCASE_BASE_URL)
        page.bring_to_front()

        print("\n" + "=" * 60)
        print("  SESIÓN REESTAURADA")
        print("-" * 60)
        print("  Puedes navegar libremente en la ventana de Chrome.")
        print("  La sesión debería estar activa si los cookies no han expirado.")
        print("\n  >>> Presiona ENTER para cerrar el navegador y terminar.")
        print("=" * 60)
        
        input()

        # Antes de cerrar, opcionalmente podrías actualizar el estado si navegaste y hubo cambios
        # context.storage_state(path=state_path) # Descomentar si se quiere guardar cambios de sesión
        
        browser.close()

if __name__ == "__main__":
    main()
