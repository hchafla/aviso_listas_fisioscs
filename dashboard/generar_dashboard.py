import csv
from datetime import datetime, timedelta
import json
from collections import defaultdict, Counter

# Fecha de referencia actual del sistema (ajustada al entorno de logs: 2026-01-06)
FECHA_ACTUAL = datetime(2026, 1, 6, 23, 33, 0)

def parsear_fecha(fecha_str):
    try:
        return datetime.strptime(fecha_str.strip(), "%d/%m/%y, %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(fecha_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

def clasificar_actividad(actualizaciones_30d, dias_activos_30d):
    if actualizaciones_30d >= 10 or dias_activos_30d >= 6:
        return "Muy activa"
    elif actualizaciones_30d >= 6 or dias_activos_30d >= 4:
        return "Alta"
    elif actualizaciones_30d >= 3 or dias_activos_30d >= 2:
        return "Media"
    elif actualizaciones_30d >= 1 or dias_activos_30d >= 1:
        return "Baja"
    else:
        return "Muy baja"

def generar_dashboard_data(ruta_csv):
    gerencias_data = defaultdict(list)
    
    # 1. Lectura y agrupación por gerencia (Columna B: Gerencia / Nombre)
    with open(ruta_csv, mode='r', encoding='utf-8') as f:
        lector = csv.reader(f)
        for fila in lector:
            if len(fila) < 2:
                continue
            fecha = parsear_fecha(fila[0])
            gerencia = fila[1].strip()
            if not fecha or not gerencia or gerencia == "NO_HEADER":
                continue
            
            gerencias_data[gerencia].append({
                "datetime": fecha,
                "fecha_str": fecha.strftime("%Y-%m-%d"),
                "mes_str": fecha.strftime("%Y-%m"),
                "anio": fecha.year
            })

    resultado_final = []

    for gerencia, eventos in gerencias_data.items():
        # Ordenar cronológicamente
        eventos.sort(key=lambda x: x["datetime"])
        
        # Último llamamiento
        ultimo_evento = eventos[-1]
        fecha_ultimo = ultimo_evento["datetime"]
        dias_desde_ultimo = (FECHA_ACTUAL - fecha_ultimo).days
        
        # Filtros temporales para métricas de últimos 30 días
        hace_30_dias = FECHA_ACTUAL - timedelta(days=30)
        eventos_30d = [e for e in eventos if e["datetime"] >= hace_30_dias]
        dias_activos_30d = len(set(e["fecha_str"] for e in eventos_30d))
        actualizaciones_30d = len(eventos_30d)
        
        clasificacion = clasificar_actividad(actualizaciones_30d, dias_activos_30d)
        
        # Heatmap diario (conteo de eventos por fecha real)
        conteo_dias = Counter(e["fecha_str"] for e in eventos)
        heatmap_diario = dict(sorted(conteo_dias.items()))
        
        # Histograma de frecuencias de actualizaciones por día
        frecuencias_por_dia = list(conteo_dias.values())
        histograma_contador = Counter(frecuencias_por_dia)
        histograma = [{"intervalo": str(k), "frecuencia": v} for k, v in sorted(histograma_contador.items())]

        # Evolución temporal (acumulado real o eventos por fecha)
        evolucion_temporal = [{"fecha": fecha, "actualizaciones": count} for fecha, count in heatmap_diario.items()]

        # Consulta personalizada (histórico agregado por ventanas)
        def calcular_ventana(dias_ventana):
            if dias_ventana is None:
                evs = eventos
                dias_totales_ventana = (eventos[-1]["datetime"] - eventos[0]["datetime"]).days + 1 if eventos else 1
            else:
                limite = FECHA_ACTUAL - timedelta(days=dias_ventana)
                evs = [e for e in eventos if e["datetime"] >= limite]
                dias_totales_ventana = dias_ventana
            
            dias_con_act = len(set(e["fecha_str"] for e in evs))
            porcentaje = round((dias_con_act / dias_totales_ventana) * 100, 2) if dias_totales_ventana > 0 else 0.0
            ultima_f = evs[-1]["fecha_str"] if evs else "No disponible"
            
            return {
                "total_actualizaciones": len(evs),
                "dias_con_actividad": dias_con_act,
                "porcentaje_dias": porcentaje,
                "ultima_fecha": ultima_f
            }

        consulta_personalizada = {
            "ultimos_7_dias": calcular_ventana(7),
            "ultimos_15_dias": calcular_ventana(15),
            "ultimos_30_dias": calcular_ventana(30),
            "ultimos_90_dias": calcular_ventana(90),
            "ultimos_180_dias": calcular_ventana(180),
            "historico_completo": calcular_ventana(None)
        }

        # Récords
        max_en_dia = max(frecuencias_por_dia) if frecuencias_por_dia else 0
        meses_counter = Counter(e["mes_str"] for e in eventos)
        mes_mas_activo = meses_counter.most_common(1)[0][0] if meses_counter else "No disponible"
        anios_counter = Counter(e["anio"] for e in eventos)
        anio_mas_activo = anios_counter.most_common(1)[0][0] if anios_counter else "No disponible"
        dia_mas_cambios = max(conteo_dias, key=conteo_dias.get) if conteo_dias else "No disponible"

        records = {
            "mayor_numero_alcanzado_en_dia": max_en_dia,
            "mes_con_mas_actividad": mes_mas_activo,
            "anio_con_mas_actividad": anio_mas_activo,
            "dia_con_mas_cambios": dia_mas_cambios
        }

        # Estructura final por gerencia
        gerencia_obj = {
            "gerencia_id": gerencia.replace(" ", "_").upper(),
            "nombre_gerencia": gerencia,
            "fecha_ultimo_llamamiento": fecha_ultimo.strftime("%Y-%m-%d %H:%M:%S"),
            "dias_desde_ultimo_llamamiento": dias_desde_ultimo,
            "clasificacion_actividad": clasificacion,
            "actualizaciones_ultimos_30_dias": actualizaciones_30d,
            "dias_activos_ultimos_30_dias": dias_activos_30d,
            "consulta_personalizada": consulta_personalizada,
            "heatmap_diario": heatmap_diario,
            "histograma": histograma,
            "evolucion_temporal": evolucion_temporal,
            "records": records
        }
        
        resultado_final.append(gerencia_obj)

    # Guardar a archivo JSON definitivo
    with open("dashboard.json", "w", encoding="utf-8") as f_json:
        json.dump(resultado_final, f_json, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    generar_dashboard_data("logs_20260106-2333.csv")
