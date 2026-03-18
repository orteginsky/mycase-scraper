# config/playwright_settings.py
from pathlib import Path

# Directorio donde se guarda el perfil persistente de Chrome
USER_DATA_DIR = Path(r"C:\ChromeProfiles\mycase_pw")

# Canal preferido (Chrome o Chromium)
CHROME_CHANNEL = "chrome"

# Mostrar o no el navegador
HEADLESS = False  # cámbialo a True cuando ya no necesites ver el navegador
