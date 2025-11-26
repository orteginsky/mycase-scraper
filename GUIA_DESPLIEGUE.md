# Guía de Despliegue a Cloud Run (Español)

## ¿Qué hace este proceso?

Este proceso sube tu sesión autenticada de MyCase a Google Cloud para que **NO te pida 2FA cada vez** que ejecutes el scraper en la nube.

## Proceso Completo (Automático)

### Opción 1: Script Automático (Recomendado)

Simplemente ejecuta:

```powershell
.\deploy_completo.bat
```

Esto hará:
1. Abrir el navegador para que inicies sesión en MyCase (manual)
2. Guardar tu sesión localmente
3. Subir la sesión a Google Cloud Storage
4. Actualizar las variables de entorno en Cloud Run
5. Configurar permisos

### Opción 2: Paso a Paso (Manual)

Si prefieres hacerlo paso a paso:

#### Paso 1: Crear perfil autenticado

```powershell
python scripts\seed_playwright_profile.py
```

**IMPORTANTE:**
- Se abrirá un navegador de Chrome
- Inicia sesión en MyCase con tu usuario: `am.mendoza@mendozafirm.com`
- Completa la autenticación de dos factores (2FA)
- Si te pregunta, marca "Recordar este dispositivo"
- Espera a que veas el dashboard de MyCase
- **NO cierres el navegador manualmente**
- **NO presiones Ctrl+C**
- Regresa a la terminal y presiona ENTER

Verás:
```
✅ SUCCESS! Session saved successfully
   Cookies file: C:\ChromeProfiles\mycase_pw\Default\Cookies
```

#### Paso 2: Subir todo a Cloud Run

```powershell
python scripts\deploy_to_cloud.py
```

Este script hace automáticamente:
1. Verifica que tienes el perfil autenticado
2. Sube el perfil a Google Cloud Storage (GCS)
3. Configura permisos del service account
4. Actualiza las variables de entorno en Cloud Run:
   - `MYCASE_EMAIL=am.mendoza@mendozafirm.com`
   - `MYCASE_PASSWORD=Mendoza1998`
   - `PW_PROFILE_GCS_BUCKET=mycase-sessions-ortega-473114`
   - Y otras configuraciones necesarias

## Verificar que funcionó

### 1. Ver logs de Cloud Run

```bash
gcloud run services logs read mycase-scraper-api --region us-central1 --limit 50
```

Busca estos mensajes de éxito:
```
Profile Sync Configuration:
  GCS Bucket: mycase-sessions-ortega-473114
✅ Playwright profile synced from GCS successfully
  Cookies file exists: True
```

### 2. Probar el endpoint de salud

```powershell
# Obtener URL del servicio
gcloud run services describe mycase-scraper-api --region us-central1 --format="value(status.url)"

# Hacer una prueba (reemplaza la URL con la tuya)
curl https://mycase-scraper-api-223080314602.us-central1.run.app/health
```

Deberías ver:
```json
{
  "playwright_profile_exists": true,
  "google_credentials_configured": true
}
```

### 3. Probar enviando un mensaje

```bash
curl -X POST https://mycase-scraper-api-223080314602.us-central1.run.app/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": 12345,
    "client_name": "Cliente de Prueba",
    "message": "Mensaje de prueba desde Cloud Run"
  }'
```

Si todo funciona bien, **NO debería pedirte 2FA** porque está usando el perfil autenticado.

## ¿Por qué esto evita el 2FA?

1. **Local**: Creas un perfil de navegador persistente e inicias sesión (con 2FA)
2. **Guardado**: Las cookies y tokens de sesión se guardan en ese perfil
3. **Subida a GCS**: El perfil completo se sube a Google Cloud Storage
4. **Cloud Run**: Cuando inicia el contenedor, descarga el perfil de GCS
5. **Reutilización**: Playwright usa ese perfil con las cookies ya guardadas
6. **Sin 2FA**: MyCase reconoce la sesión y no pide autenticación de nuevo

## Mantenimiento

Las sesiones expiran eventualmente. Cuando notes que empieza a pedir 2FA de nuevo:

```powershell
# 1. Re-autenticar localmente
python scripts\seed_playwright_profile.py

# 2. Subir el nuevo perfil
python scripts\upload_profile_to_gcs.py

# 3. Reiniciar Cloud Run (forzar descarga del nuevo perfil)
gcloud run services update mycase-scraper-api --region us-central1 --update-env-vars=PROFILE_VERSION=$(Get-Date -UFormat %s)
```

## Solución de Problemas

### Error: "Profile directory is empty"

**Causa**: No ejecutaste `seed_playwright_profile.py` correctamente

**Solución**:
```powershell
python scripts\seed_playwright_profile.py
```
Asegúrate de NO interrumpir con Ctrl+C

### Error: "Invalid service account ()"

**Causa**: Cloud Run no tiene service account configurado

**Solución**: El script `deploy_to_cloud.py` lo configura automáticamente

### Error: "Authentication failed" en Cloud Run

**Causa**: El perfil no se descargó correctamente o las cookies expiraron

**Solución**:
1. Verifica que el perfil está en GCS:
   ```bash
   gcloud storage ls gs://mycase-sessions-ortega-473114/playwright-profiles/mycase/
   ```
2. Si no está, re-ejecuta el paso 2
3. Si está, puede que haya expirado - crea uno nuevo con el paso 1

### Error: "gcloud not found"

**Causa**: Google Cloud SDK no está instalado

**Solución**:
1. Instala desde: https://cloud.google.com/sdk/docs/install
2. Reinicia PowerShell
3. Ejecuta: `gcloud auth login`

## Estructura de Archivos

```
C:\ChromeProfiles\mycase_pw\           # Perfil local (Windows)
├── Default\
│   ├── Cookies                        # ← Archivo importante (sesión)
│   ├── Local Storage\                 # ← Tokens y datos
│   └── ...

Google Cloud Storage:
gs://mycase-sessions-ortega-473114/
└── playwright-profiles/
    └── mycase/
        └── profile.tar.gz             # ← Perfil comprimido

Cloud Run Container:
/app/playwright_profile/               # Perfil descargado en startup
├── Default/
│   ├── Cookies
│   └── ...
```

## Variables de Entorno Configuradas

El script automáticamente configura estas variables en Cloud Run:

| Variable | Valor |
|----------|-------|
| `MYCASE_EMAIL` | `am.mendoza@mendozafirm.com` |
| `MYCASE_PASSWORD` | `Mendoza1998` |
| `PW_PROFILE_GCS_BUCKET` | `mycase-sessions-ortega-473114` |
| `PW_PROFILE_GCS_PREFIX` | `playwright-profiles/mycase/` |
| `PW_HEADLESS` | `true` |
| `PW_USER_DATA_DIR` | `/app/playwright_profile` |
| `DOWNLOAD_DIR` | `/tmp/downloads` |

## Comandos Útiles

```bash
# Ver logs en tiempo real
gcloud run services logs tail mycase-scraper-api --region us-central1

# Ver estado del servicio
gcloud run services describe mycase-scraper-api --region us-central1

# Ver todas las variables de entorno
gcloud run services describe mycase-scraper-api --region us-central1 --format="value(spec.template.spec.containers[0].env)"

# Actualizar solo una variable
gcloud run services update mycase-scraper-api --region us-central1 --update-env-vars=MYCASE_EMAIL=nuevo@email.com

# Listar archivos en GCS
gcloud storage ls gs://mycase-sessions-ortega-473114/playwright-profiles/mycase/
```
