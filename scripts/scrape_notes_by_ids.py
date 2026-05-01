import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Load .env from project root
_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_ROOT / ".env")

from src.core.context_manager import mycase_auto_session
from src.scraping.notes import extract_case_notes
from src.utils.logger import get_logger

logger = get_logger(__name__)

# List of IDs to process
ENTITY_IDS = [
45837441
]
SCRAPE_TYPE = "VAWA DA" # Parámetro 'type' para identificación

OUTPUT_FILE = _ROOT / "data" / "notes_extraction.jsonl"

def main():
    # Ensure data directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting notes extraction for %d IDs", len(ENTITY_IDS))
    
    results_count = 0
    errors_count = 0
    
    with mycase_auto_session() as page:
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            for entity_id in ENTITY_IDS:
                try:
                    # Obtener la lista de notas
                    result = extract_case_notes(page, entity_id, entity_type="case", type=SCRAPE_TYPE)
                    notes_list = result["notes"]
                    
                    # Estructurar el registro para el JSONL
                    record = {
                        "entity_id": entity_id,
                        "type": result.get("type"), # Nuevo parámetro
                        "notes_count": len(notes_list),
                        "notes": notes_list,
                        "extracted_at": datetime.utcnow().isoformat() + "Z"
                    }
                    
                    # Escribir al JSONL (una línea por cada ID)
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f.flush() # Asegurar escritura en disco
                    
                    results_count += 1
                    logger.info("Successfully extracted %d notes for %s", len(notes_list), entity_id)
                    
                except Exception as e:
                    logger.error("Error processing entity_id %s: %s", entity_id, e)
                    errors_count += 1
                    # Log error in JSONL as well for traceability
                    error_entry = {
                        "entity_id": entity_id,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")
                    f.flush()

    logger.info("Extraction complete. Results: %d, Errors: %d", results_count, errors_count)
    logger.info("Output saved to: %s", OUTPUT_FILE)

if __name__ == "__main__":
    main()
