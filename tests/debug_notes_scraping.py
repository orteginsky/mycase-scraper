import sys
import json
from pathlib import Path

# Configurar el root del proyecto para importaciones
_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_ROOT / ".env")

from src.core.context_manager import mycase_auto_session
from src.scraping.notes import extract_case_notes
from src.utils.logger import get_logger

# Configurar logger para ver detalles en consola
logger = get_logger(__name__)

# ID para debug (Hardcoded)
DEBUG_CASE_ID = 45958707 
DEBUG_ENTITY_TYPE = "case" # Puede ser "lead" o "case"

def debug_extraction():
    print("=" * 60)
    print(f" DEBUG: Extrayendo notas para {DEBUG_ENTITY_TYPE} ID: {DEBUG_CASE_ID}")
    print("=" * 60)
    
    try:
        with mycase_auto_session() as page:
            # Ejecutar el scraping
            result = extract_case_notes(page, DEBUG_CASE_ID, entity_type=DEBUG_ENTITY_TYPE)
            notes = result["notes"]
            
            # Mostrar resultados
            if not notes:
                print("\n[!] No se extrajeron notas o el caso no existe.")
                return

            print(f"\n[✓] Se encontraron {len(notes)} notas (Type: {result.get('type')}):")
            print("-" * 60)
            
            for i, note in enumerate(notes, 1):
                print(f"NOTA #{i}")
                print(f"  ID:      {note.get('id')}")
                print(f"  Subject: {note.get('subject')}")
                print(f"  Author:  {note.get('author')}")
                print(f"  Date:    {note.get('date')}")
                # Mostrar solo los primeros 150 caracteres del body para no saturar la consola
                body_preview = note.get("body", "").replace("\n", " ")[:150]
                print(f"  Body:    {body_preview}...")
                print("-" * 40)

            # También guardamos el resultado completo en un JSON temporal para inspección profunda
            debug_json = _ROOT / "data" / f"debug_notes_{DEBUG_CASE_ID}.json"
            debug_json.parent.mkdir(exist_ok=True)
            with open(debug_json, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
            
            print(f"\n[i] Resultado completo guardado en: {debug_json}")

    except Exception as e:
        logger.exception("Error durante el debug de notas: %s", e)
        print(f"\n[X] ERROR CRÍTICO: {e}")

if __name__ == "__main__":
    debug_extraction()
