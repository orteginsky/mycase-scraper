# utils/logger.py
import logging
import sys
from pathlib import Path

# Carpeta donde se guardarán los logs
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

# Ruta del archivo de logs
LOG_FILE = LOG_DIR / "scraping.log"

def get_logger(name: str = "scraping"):
    """
    Devuelve un logger configurado con salida a consola y archivo.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # Evita duplicar handlers si se llama varias veces

    logger.setLevel(logging.DEBUG)

    # 📌 Formato uniforme
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # INFO y arriba en consola
    console_handler.setFormatter(formatter)

    # Handler de archivo
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # DEBUG y arriba en archivo
    file_handler.setFormatter(formatter)

    # Agregar handlers al logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
