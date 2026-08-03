from datetime import datetime, timedelta

def calcular_metricas_gerencia(eventos, todas_las_gerencias=None):
    # Usar la fecha actual real del sistema (o la fecha de congelación de ejecución)
    fecha_actual = datetime.now()
    
    # Ordenar eventos cronológicamente
    eventos_ordenados = sorted(eventos, key=lambda x: x["datetime"])
    
    if not eventos_ordenados:
        return {
            "dias_desde_ultimo_llamamiento": None,
            "fecha_ultimo_llamamiento": None,
            "actualizaciones_ultimos_30_dias": 0,
            "dias_activos_ultimos_30_dias": 0,
            "frecuencia_historica_dias": None,
            "media_mensual": 0.0,
            "total_actualizaciones_historicas": 0
        }
    
    ultimo_evento = eventos_ordenados[-1]["datetime"]
    dias_desde_ultimo = (fecha_actual - ultimo_evento).days
    
    # Ventana de los últimos 30 días reales
    hace_30_dias = fecha_actual - timedelta(days=30)
    eventos_30d = [e for e in eventos_ordenados if e["datetime"] >= hace_30_dias]
    
    actualizaciones_30d = len(eventos_30d)
    dias_activos_30d = len(set(e["datetime"].date() for e in eventos_30d))
    
    # Métricas temporales objetivas y puras
    total_dias_historico = (ultimo_evento - eventos_ordenados[0]["datetime"]).days
    total_eventos = len(eventos_ordenados)
    
    # Cálculo preciso basado en los intervalos reales entre eventos
    frecuencia_historica = (
        round(total_dias_historico / (total_eventos - 1), 1)
        if total_eventos > 1 else None
    )
    
    # Media mensual basada en el histórico de actividad
    meses_totales = max(1, total_dias_historico / 30.44)
    media_mensual = round(total_eventos / meses_totales, 1)

    return {
        "dias_desde_ultimo_llamamiento": dias_desde_ultimo,
        "fecha_ultimo_llamamiento": ultimo_evento.strftime("%Y-%m-%d"),
        "actualizaciones_ultimos_30_dias": actualizaciones_30d,
        "dias_activos_ultimos_30_dias": dias_activos_30d,
        "frecuencia_historica_dias": frecuencia_historica,
        "media_mensual": media_mensual,
        "total_actualizaciones_historicas": total_eventos
    }
