@echo off
REM Script completo para desplegar a Cloud Run
REM Este script hace todo el proceso automaticamente

echo ========================================
echo DESPLIEGUE COMPLETO A CLOUD RUN
echo ========================================
echo.

REM Paso 1: Crear perfil autenticado (manual)
echo PASO 1: Crear perfil autenticado
echo ========================================
echo IMPORTANTE:
echo - NO cierres el navegador manualmente
echo - NO presiones Ctrl+C
echo - Espera a que termine el login y presiona ENTER
echo.
pause
python scripts\seed_playwright_profile.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudo crear el perfil autenticado
    pause
    exit /b 1
)

echo.
echo ========================================
echo PASO 2: Subiendo todo a Cloud Run
echo ========================================
echo.
python scripts\deploy_to_cloud.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: El despliegue fallo
    pause
    exit /b 1
)

echo.
echo ========================================
echo DESPLIEGUE COMPLETADO EXITOSAMENTE
echo ========================================
echo.
echo El servicio ya esta actualizado en Cloud Run
echo con tu perfil autenticado y tus credenciales.
echo.
pause
