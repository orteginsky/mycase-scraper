# Usa la imagen oficial con Chromium y dependencias listas
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Ajustes básicos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_DISABLE_RUN_AS_NODE=1

WORKDIR /app

# Copia e instala deps Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia el código
COPY . .

# Dirs de trabajo
RUN mkdir -p /app/playwright_profile /app/logs /tmp/downloads

# ENV para Linux/Cloud Run
ENV PW_USER_DATA_DIR=/app/playwright_profile
ENV DOWNLOAD_DIR=/tmp/downloads
ENV PW_HEADLESS=true

EXPOSE 8080

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]
