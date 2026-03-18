import re
import unicodedata
from typing import Optional

def sanitize_folder_name(name: Optional[str]) -> str:
    """
    Normaliza un nombre de carpeta para que sea válido en Windows.
    - Reemplaza caracteres no permitidos <>:"/\\|?* por '_'
    - Normaliza acentos (NFKD)
    - Elimina caracteres de control
    - Quita puntos o espacios finales
    """
    if name:
        name = name.strip()
        # Normalizar acentos (é → e, ñ → n, etc.)
        name = unicodedata.normalize("NFKD", name)
        name = "".join(c for c in name if not unicodedata.combining(c))

        # Reemplazar caracteres prohibidos
        name = re.sub(r'[<>:"/\\|?*]', "_", name)

        # Eliminar caracteres de control (0-31) y no imprimibles
        name = re.sub(r"[\x00-\x1f]", "_", name)

        # Reemplazar espacios consecutivos por uno solo
        name = re.sub(r"\s+", "_", name)

        # Quitar puntos o espacios finales (no válidos en Windows)
        name = name.rstrip(" .")
    else:
        name = "cliente_sin_nombre"
    # Si queda vacío, usar un nombre genérico
    return name
