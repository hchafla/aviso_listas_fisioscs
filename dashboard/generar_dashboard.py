from datetime import datetime, timedelta
from collections import defaultdict

def calcular_metricas_gerencia(eventos, fecha_referencia=None):
    """
    Calcula métricas puras y objetivas para una gerencia a partir de su histórico de eventos.
    
    :param eventos: Lista de diccionarios con al menos [{"datetime": datetime(...), "numero_lista": int}, ...]
    :param fecha_referencia: Fecha máxima de corte para cálculos relativos (ej. último evento global). 
                             Si es None, se usa la fecha del último evento de la gerencia.
    """
    if not eventos:
        return {
            "dias_desde_ultimo_llamamiento": None,
            "fecha_ultimo_llamamiento": None,
            "actualizaciones_ultimos_30_dias": 0,
            "dias_activos_ultimos_30_dias": 0,
            "frecuencia_historica_dias": None,
            "media_mensual": 0.0,
            "total_actualizaciones_historicas": 0,
            "maximo_historico_numero": None
        }
    
    # Ordenar eventos cronológicamente
    eventos_ordenados = sorted(eventos, key=lambda x: x["datetime"])
    
    ultimo_evento_dt = eventos_ordenados[-1]["datetime"]
    fecha_ref = fecha_referencia if fecha_referencia else ultimo_evento_dt
    
    dias_desde_ultimo = (fecha_ref - ultimo_evento_dt).days
    
    # Ventanas temporales basadas en la fecha de referencia
    hace_30_dias = fecha_ref - timedelta(days=30)
    eventos_30d = [e for e in eventos_ordenados if e["datetime"] >= hace_30_dias]
    
    actualizaciones_30d = len(eventos_30d)
    dias_activos_30d = len(set(e["datetime"].date() for e in eventos_30d))
    
    # Cálculo robusto de la frecuencia histórica basado en deltas reales entre llamamientos
    deltas_dias = []
    for i in range(1, len(eventos_ordenados)):
        delta = (eventos_ordenados[i]["datetime"] - eventos_ordenados[i-1]["datetime"]).days
        if delta > 0:  # Evitar duplicados exactos el mismo día en el cálculo de intervalos
            deltas_dias.append(delta)
            
    frecuencia_historica = (
        round(sum(deltas_dias) / len(deltas_dias), 1)
        if deltas_dias else 0.0
    )
    
    # Media mensual basada en meses calendario reales con actividad o distribución de spans
    primer_evento_dt = eventos_ordenados[0]["datetime"]
    total_dias_historico = (ultimo_evento_dt - primer_evento_dt).days
    total_eventos = len(eventos_ordenados)
    
    if total_dias_historico > 0:
        # Contar meses únicos presentes en el histórico
        meses_unicos = len(set((e["datetime"].year, e["datetime"].month) for e in eventos_ordenados))
        media_mensual = round(total_eventos / max(1, meses_unicos), 1)
    else:
        media_mensual = float(total_eventos)

    # Máximo histórico alcanzado en esta gerencia
    maximo_historico = max((e.get("numero_lista", 0) for e in eventos_ordenados), default=None)

    return {
        "dias_desde_ultimo_llamamiento": max(0, dias_desde_ultimo),
        "fecha_ultimo_llamamiento": ultimo_evento_dt.strftime("%Y-%m-%d"),
        "actualizaciones_ultimos_30_dias": actualizaciones_30d,
        "dias_activos_ultimos_30_dias": dias_activos_30d,
        "frecuencia_historica_dias": frecuencia_historica,
        "media_mensual": media_mensual,
        "total_actualizaciones_historicas": total_eventos,
        "maximo_historico_numero": maximo_historico
    }
