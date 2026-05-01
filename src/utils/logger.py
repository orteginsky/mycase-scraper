# utils/logger.py
import logging
import sys

def get_logger(name: str = "scraping"):
    """
    Devuelve un logger configurado con salida a sys.stdout para Cloud Run.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    # Formato simple y limpio para Cloud Logging
    formatter = logging.Formatter(
        "[%(levelname)s] %(name)s: %(message)s"
    )

    # Handler de consola (Cloud Run captura stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Agregar handler al logger
    logger.addHandler(console_handler)

    return logger
