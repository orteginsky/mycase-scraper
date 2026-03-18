"""
Convierte state.json a base64 para usarlo como variable de entorno en Docker.

Uso:
    python -m src.scripts.exportar_estado

Resultado: imprime PW_STATE_B64=... y lo guarda en .env.state
"""
import base64
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from core import config


def main() -> None:
    state_file = config.STATE_FILE

    if not state_file.exists():
        print(f"ERROR: No se encontró {state_file}")
        print("Ejecuta primero: python -m src.scripts.crear_sesion")
        sys.exit(1)

    content = state_file.read_bytes()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"ERROR: {state_file} no es JSON válido: {e}")
        sys.exit(1)

    cookies = data.get("cookies", [])
    encoded = base64.b64encode(content).decode("ascii")

    print("=" * 65)
    print("Agrega esta línea a tu .env (o como variable de entorno en Docker):")
    print("=" * 65)
    print(f"PW_STATE_B64={encoded}")
    print("=" * 65)
    print(f"\nCookies incluidas : {len(cookies)}")
    print(f"Tamaño original   : {len(content)} bytes")
    print(f"Tamaño codificado : {len(encoded)} caracteres")

    out_file = state_file.parent / ".env.state"
    out_file.write_text(f"PW_STATE_B64={encoded}\n", encoding="ascii")
    print(f"\nTambién guardado en: {out_file}")
    print("Puedes copiar el contenido de ese archivo a tu .env")


if __name__ == "__main__":
    main()
