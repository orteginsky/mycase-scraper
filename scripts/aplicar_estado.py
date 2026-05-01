"""
Script 2.5/3: Aplica PW_STATE_B64 del archivo .env.state al .env principal.

Soluciona el problema de que python-dotenv no soporta valores multilínea:
si pegas el base64 manualmente en el editor, este lo parte en múltiples
líneas y la variable queda TRUNCADA e inválida.

Este script:
  1. Lee la variable correcta desde .env.state (siempre una sola línea)
  2. Elimina cualquier entrada PW_STATE_B64 previa del .env (incluyendo
     líneas de continuación)
  3. Agrega la variable nueva en una sola línea al final del .env
  4. Valida que el JSON del state sea decodificable

Uso:
    python -m scripts.aplicar_estado

Flujo completo:
    python -m scripts.crear_sesion      # 1. genera state.json
    python -m scripts.exportar_estado   # 2. genera .env.state
    python -m scripts.aplicar_estado    # 3. aplica al .env  ← este script
    python -m scripts.validar_sesion    # 4. verifica la sesión
"""
import base64
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Rutas relativas a la raíz del proyecto (1 nivel arriba de scripts/)
_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE   = _ROOT / ".env"
STATE_FILE = _ROOT / ".env.state"


def _read_state_value() -> str:
    """Lee PW_STATE_B64 desde .env.state y devuelve el valor base64 (sin clave)."""
    if not STATE_FILE.exists():
        print(f"ERROR: No se encontró {STATE_FILE}")
        print("Ejecuta primero: python -m scripts.exportar_estado")
        sys.exit(1)

    line = STATE_FILE.read_text(encoding="ascii").strip()
    if not line.startswith("PW_STATE_B64="):
        print(f"ERROR: {STATE_FILE} no tiene el formato esperado (PW_STATE_B64=...)")
        sys.exit(1)

    value = line.split("=", 1)[1]
    return value


def _validate_base64(value: str) -> dict:
    """Valida que el base64 sea JSON válido y retorna el dict."""
    try:
        decoded = base64.b64decode(value)
        data = json.loads(decoded)
        return data
    except Exception as e:
        print(f"ERROR: El valor en .env.state no es JSON válido en base64: {e}")
        sys.exit(1)


def _patch_env(value: str) -> None:
    """
    Reemplaza (o agrega) PW_STATE_B64 en el .env en una sola línea.
    Elimina líneas de continuación huérfanas (base64 sin '=').
    """
    if not ENV_FILE.exists():
        print(f"AVISO: {ENV_FILE} no existe — se creará uno nuevo.")
        ENV_FILE.write_text(f"PW_STATE_B64={value}\n", encoding="utf-8")
        return

    lines = ENV_FILE.read_text(encoding="utf-8").split("\n")
    new_lines = []
    skip_continuation = False

    for line in lines:
        if line.startswith("PW_STATE_B64="):
            # Marcar que las próximas "continuaciones" deben omitirse
            skip_continuation = True
            continue  # se reemplazará al final

        if skip_continuation:
            # Identificar líneas de continuación: solo base64 chars sin '='
            stripped = line.strip()
            is_continuation = stripped and not stripped.startswith("#") and "=" not in stripped
            if is_continuation:
                continue  # saltar
            else:
                skip_continuation = False  # línea normal, fin de la continuación

        new_lines.append(line)

    # Asegurarse de que haya una línea en blanco separadora si el archivo no termina en newline
    if new_lines and new_lines[-1].strip():
        new_lines.append("")

    new_lines.append(f"PW_STATE_B64={value}")
    new_lines.append("")  # newline final

    ENV_FILE.write_text("\n".join(new_lines), encoding="utf-8")


def main() -> None:
    print("=" * 60)
    print("  APLICAR PW_STATE_B64 AL .env")
    print("=" * 60)

    # 1. Leer valor desde .env.state
    print(f"\n  Origen  : {STATE_FILE}")
    value = _read_state_value()

    # 2. Validar
    data = _validate_base64(value)
    cookies = data.get("cookies", [])
    origins = data.get("origins", [])
    print(f"  Cookies : {len(cookies)}")
    print(f"  Origins : {len(origins)}")

    # 3. Parchear .env
    _patch_env(value)
    print(f"\n  ✅ PW_STATE_B64 aplicada correctamente en: {ENV_FILE}")
    print()
    print("Siguiente paso:")
    print("  python -m scripts.validar_sesion    # verificar la sesión")
    print("=" * 60)


if __name__ == "__main__":
    main()
