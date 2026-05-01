"""
Valida que el estado de sesión (state.json o PW_STATE_B64) esté activo en MyCase.

Fuente del estado (en orden de prioridad):
  1. Variable de entorno PW_STATE_B64  (base64 del state.json)
  2. Archivo local definido en STATE_FILE (default: state.json)

Uso:
    python -m src.scripts.validar_sesion

    # Con variable de entorno directamente:
    PW_STATE_B64=<valor> python -m src.scripts.validar_sesion

Códigos de salida:
    0 — sesión activa
    1 — sesión expirada, inválida, o estado no encontrado
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from src.core import config
from src.core.context_manager import load_state_path, _create_state_context, check_session_active


def main() -> int:
    print("=" * 55)
    print("  VALIDACIÓN DE SESIÓN MYCASE")
    print("=" * 55)

    state_path = load_state_path()

    if not state_path:
        print("\nERROR: No se encontró ningún estado de sesión.")
        print("  - Define PW_STATE_B64 en tu .env, o")
        print(f"  - Ejecuta `python -m src.scripts.crear_sesion` para generar {config.STATE_FILE}")
        return 1

    print(f"\n  Estado  : {state_path}")
    print(f"  URL     : {config.MYCASE_BASE_URL}")
    print()

    p, browser, context, page = _create_state_context(state_path)
    try:
        print(f"  Navegando a {config.MYCASE_BASE_URL} ...")
        try:
            page.goto(config.MYCASE_BASE_URL, timeout=30_000)
        except Exception as e:
            print(f"\nERROR al navegar: {e}")
            return 1

        activa = check_session_active(page)
        url_final = page.url
    finally:
        context.close()
        browser.close()
        p.stop()

    print()
    print("=" * 55)
    if activa:
        print("  RESULTADO: sesión ACTIVA")
        print(f"  URL final : {url_final}")
        print("=" * 55)
        print()
        print("La sesión es válida. Para usar en Docker:")
        print("  python -m src.scripts.exportar_estado")
        return 0
    else:
        print("  RESULTADO: sesión EXPIRADA o INVÁLIDA")
        print(f"  URL final : {url_final}")
        print("=" * 55)
        print()
        print("Renueva la sesión:")
        print("  python -m src.scripts.crear_sesion")
        print("  python -m src.scripts.exportar_estado")
        return 1


if __name__ == "__main__":
    sys.exit(main())
