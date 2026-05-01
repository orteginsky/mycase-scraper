"""
Convierte state.json a base64 para usarlo como variable de entorno en Docker.

Uso:
    python -m src.scripts.exportar_estado

Resultado: imprime PW_STATE_B64=... y lo guarda en .env.state
"""
import base64
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.core import config


def get_state_base64(state_file: Path) -> str:
    """Lee un archivo de estado y lo devuelve en base64."""
    if not state_file.exists():
        raise FileNotFoundError(f"No se encontró {state_file}")
    content = state_file.read_bytes()
    # Validar JSON básico
    json.loads(content)
    return base64.b64encode(content).decode("ascii")


def main() -> None:
    state_file = config.STATE_FILE

    try:
        encoded = get_state_base64(state_file)
        content_len = len(state_file.read_bytes())
        
        # Para contar cookies leemos los datos
        data = json.loads(state_file.read_bytes())
        cookies = data.get("cookies", [])

    except Exception as e:
        print(f"❌ ERROR al procesar estado: {e}")
        sys.exit(1)

    print("=" * 65)
    print(f"Cookies incluidas : {len(cookies)}")
    print(f"Tamaño original   : {content_len} bytes")
    print(f"Tamaño codificado : {len(encoded)} caracteres")

    out_file = state_file.parent / ".env.state"
    out_file.write_text(f"PW_STATE_B64={encoded}\n", encoding="ascii")

    print(f"\nEstado guardado en: {out_file}")
    print()
    print("=" * 65)
    print("  CÓMO APLICAR AL .env  (IMPORTANTE)")
    print("=" * 65)
    print()
    print("  ⚠  NO copies la variable directamente al .env con un editor:")
    print("     python-dotenv NO soporta valores que ocupen varias líneas.")
    print("     Si el editor parte la línea, la variable quedará TRUNCADA.")
    print()
    print("  ✅  Usa el siguiente comando para aplicarla de forma segura:")
    print()
    print(f"      python -m src.scripts.aplicar_estado")
    print()
    print("  O manualmente desde la terminal (una sola línea):")
    print(f"      grep PW_STATE_B64 .env.state >> .env")
    print("      # (y elimina la entrada anterior de PW_STATE_B64 en .env)")
    print("=" * 65)


if __name__ == "__main__":
    main()
