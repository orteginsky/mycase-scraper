import csv
import json
from pathlib import Path

def csv_to_json_files(csv_path: str):
    # 📁 Carpeta donde se guardarán los JSONs
    output_dir = Path(__file__).parent / "json_output"
    output_dir.mkdir(exist_ok=True)

    # 📄 Leer CSV
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Limpiar datos
            record = {k.strip(): (v.strip() if v else "") for k, v in row.items()}

            # Obtener ID y nombre de archivo
            record_id = record.get("ID")
            if not record_id:
                print(f"⚠️  Fila sin ID, omitida: {record}")
                continue

            json_filename = f"{record_id}.json"
            json_path = output_dir / json_filename

            # Guardar JSON
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(record, json_file, indent=4, ensure_ascii=False)

            print(f"✅ Archivo creado: {json_path.name}")

    print(f"\n📦 Conversión completada. Archivos guardados en: {output_dir.resolve()}")


if __name__ == "__main__":
    # 👉 Cambia este nombre si tu CSV tiene otro
    csv_filename = "case_details_resultado_1_a_100.csv"
    csv_to_json_files(csv_filename)
