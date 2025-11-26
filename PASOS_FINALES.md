# Pasos Finales para Desplegar a Cloud Run

## ✅ Ya completaste: Crear perfil autenticado

Ya tienes tu perfil con la sesión guardada en:
```
C:\ChromeProfiles\mycase_pw
```

## Paso 1: Subir el perfil a GCS

En PowerShell:

```powershell
python scripts\subir_perfil.py
```

Este comando:
- Empaqueta tu perfil local
- Lo sube a `gs://mycase-sessions-ortega-473114/playwright-profiles/mycase/profile.tar.gz`
- Te muestra el comando para actualizar Cloud Run

## Paso 2: Actualizar Cloud Run

**Opción A: Desde Google Cloud Shell** (Recomendado)

1. Ve a: https://console.cloud.google.com/
2. Haz clic en el ícono de Cloud Shell (esquina superior derecha)
3. Ejecuta este comando:

```bash
gcloud run services update mycase-scraper-api \
  --region us-central1 \
  --set-env-vars="\
MYCASE_EMAIL=am.mendoza@mendozafirm.com,\
MYCASE_PASSWORD=Mendoza1998,\
PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114,\
PW_PROFILE_GCS_PREFIX=playwright-profiles/mycase/,\
PW_HEADLESS=true,\
PW_USER_DATA_DIR=/app/playwright_profile,\
DOWNLOAD_DIR=/tmp/downloads"
```

4. Configura permisos del service account:

```bash
# Obtener service account
SA_EMAIL="$(gcloud run services describe mycase-scraper-api \
  --region us-central1 \
  --format='value(spec.template.spec.serviceAccount)')"

# Si está vacío, usar el default
if [ -z "$SA_EMAIL" ]; then
  SA_EMAIL="ortega-473114-compute@developer.gserviceaccount.com"
fi

echo "Service Account: $SA_EMAIL"

# Otorgar permisos
gcloud storage buckets add-iam-policy-binding gs://mycase-sessions-ortega-473114 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"
```

**Opción B: Desde tu PC** (Si tienes gcloud instalado)

```powershell
gcloud run services update mycase-scraper-api `
  --region us-central1 `
  --set-env-vars="MYCASE_EMAIL=am.mendoza@mendozafirm.com,MYCASE_PASSWORD=Mendoza1998,PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114,PW_PROFILE_GCS_PREFIX=playwright-profiles/mycase/,PW_HEADLESS=true,PW_USER_DATA_DIR=/app/playwright_profile,DOWNLOAD_DIR=/tmp/downloads"
```

## Paso 3: Verificar que funcionó

Espera 1-2 minutos y revisa los logs:

```bash
gcloud run services logs read mycase-scraper-api --region us-central1 --limit 50
```

Busca estos mensajes de éxito:
```
✅ Playwright profile synced from GCS successfully
  Cookies file exists: True
```

## Paso 4: Probar el servicio

```bash
# Obtener URL
SERVICE_URL=$(gcloud run services describe mycase-scraper-api \
  --region us-central1 \
  --format='value(status.url)')

# Probar health check
curl $SERVICE_URL/health

# Probar envío de mensaje
curl -X POST $SERVICE_URL/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": 12345,
    "client_name": "Prueba",
    "message": "Mensaje de prueba"
  }'
```

## ¿Qué pasa ahora?

1. Cloud Run descarga el perfil de GCS al iniciar
2. Playwright usa ese perfil con las cookies ya guardadas
3. MyCase reconoce la sesión y **NO pide 2FA**
4. El scraper funciona automáticamente

## Mantenimiento

Las cookies expiran eventualmente (cada 30-90 días). Cuando empiece a pedir 2FA de nuevo:

```powershell
# 1. Re-autenticar
python scripts\seed_playwright_profile.py

# 2. Re-subir
python scripts\subir_perfil.py

# 3. Reiniciar Cloud Run (fuerza re-descarga)
gcloud run services update mycase-scraper-api --region us-central1 --update-env-vars=PROFILE_VERSION=$(date +%s)
```

## Resumen de URLs

- **Cloud Console**: https://console.cloud.google.com/run?project=ortega-473114
- **Cloud Shell**: https://shell.cloud.google.com
- **Logs**: https://console.cloud.google.com/logs/query?project=ortega-473114
- **Service**: https://mycase-scraper-api-223080314602.us-central1.run.app
