csv
from datetime import datetime
import json
from collections import defaultdict

def parsear_fecha(fecha_str):
    try:
        return datetime.strptime(fecha_str.strip(), "%d/%m/%y, %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(fecha_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

def generar_dashboard_data(ruta_csv):
    gerencias_data = defaultdict(list)
    
    # Lectura del CSV respetando la estructura original
    with open(ruta_csv, mode='r', encoding='utf-8') as f:
        lector = csv.reader(f)
        for fila in lector:
            if len(fila) < 3:
                continue
            
            fecha = parsear_fecha(fila[0])
            gerencia = fila[1].strip()
            
            try:
                numero = int(fila[2].strip())
            except ValueError:
                continue  # Descartar filas con números no válidos
                
            # Campos opcionales si vienen en el CSV, con valores por defecto limpios
            lista = fila[3].strip() if len(fila) > 3 else "General"
            tipo = fila[4].strip() if len(fila) > 4 else "Ordinaria"

            if not fecha or not gerencia or gerencia == "NO_HEADER":
                continue
            
            # Cada evento conserva exactamente el histórico crudo solicitado
            evento = {
                "fecha": fecha.strftime("%Y-%m-%d %H:%M:%S"),
                "numero": numero,
                "lista": lista,
                "tipo": tipo
            }
            
            gerencias_data[gerencia].append(evento)

    resultado_final = []

    for gerencia, eventos in gerencias_data.items():
        # Mantener el orden cronológico original de los eventos
        eventos.sort(key=lambda x: x["fecha"])
        
        # Mantener la estructura general original de tu JSON por gerencia
        gerencia_obj = {
            "gerencia_id": gerencia.replace(" ", "_").upper(),
            "nombre_gerencia": gerencia,
            "eventos": eventos  # Histórico puro de materia prima
        }
        
        resultado_final.append(gerencia_obj)

    # Volcado limpio con la misma estructura original
    with open("dashboard.json", "w", encoding="utf-8") as f_json:
        json.dump(resultado_final, f_json, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    generar_dashboard_data("logs_20260106-2333.csv")
