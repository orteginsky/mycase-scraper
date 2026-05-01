# scripts/__init__.py
"""
Session management scripts for MyCase.

Workflow:
    1. crear_sesion.py   — opens browser for manual login (2FA), saves state.json
    2. exportar_estado.py — encodes state.json to PW_STATE_B64 for Docker/.env
    3. validar_sesion.py  — verifies session is still active (no browser needed)
    4. verificar_sesion.py — downloads state from GCS and opens browser to verify

Run any script as a module from the project root:
    python -m src.scripts.crear_sesion
    python -m src.scripts.exportar_estado
    python -m src.scripts.validar_sesion
    python -m src.scripts.verificar_sesion
"""
