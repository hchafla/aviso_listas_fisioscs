from datetime import datetime, date
import pandas as pd

def procesar_observatorio_oposiciones(df_llamamientos, numero_lista_usuario=None):
    """
    Procesa los datos de llamamientos para corregir errores lógicos,
    calcular correctamente las fechas y permitir la consulta por número de lista.
    
    :param df_llamamientos: DataFrame con columnas ['fecha', 'gerencia', 'numero_lista']
    :param numero_lista_usuario: (Opcional) Entero con el número de lista a consultar
    :return: Diccionario con la estructura limpia y lista para JSON
    """
    # Fecha de referencia actual del sistema (simulada o real)
    fecha_hoy = date(2026, 8, 3) 
    
    # Asegurar formato fecha/hora
    df_llamamientos['fecha_dt'] = pd.to_datetime(df_llamamientos['fecha'])
    df_llamamientos['solo_fecha'] = df_llamamientos['fecha_dt'].dt.date
    
    # 1. Último llamamiento global real
    idx_ultimo_global = df_llamamientos['fecha_dt'].idxmax()
    row_ultimo_global = df_llamamientos.loc[idx_ultimo_global]
    
    metadata = {
        "fecha_actualizacion_sistema": fecha_hoy.strftime("%Y-%m-%d"),
        "ultimo_llamamiento_global": {
            "fecha": str(row_ultimo_global['fecha_dt']),
            "gerencia": str(row_ultimo_global['gerencia']),
            "numero_lista": int(row_ultimo_global['numero_lista'])
        }
    }
    
    # 2. Procesar por gerencias
    gerencias_resultado = []
    gerencias_unicas = df_llamamientos['gerencia'].unique()
    
    for g in gerencias_unicas:
        df_g = df_llamamientos[df_llamamientos['gerencia'] == g]
        
        # Último llamamiento de esta gerencia específica
        row_ult_g = df_g.loc[df_g['fecha_dt'].idxmax()]
        f_ult_g = row_ult_g['solo_fecha']
        
        # CÁLCULO CORREGIDO: Días transcurridos (siempre positivo o cero)
        dias_desde = (fecha_hoy - f_ult_g).days
        if dias_desde < 0:
            dias_desde = 0
            
        # Ventanas temporales
        hace_7_dias = fecha_hoy - pd.Timedelta(days=7)
        hace_30_dias = fecha_hoy - pd.Timedelta(days=30)
        
        df_7d = df_g[df_g['solo_fecha'] >= hace_7_dias]
        df_30d = df_g[df_g['solo_fecha'] >= hace_30_dias]
        
        # CORREGIDO: Días con actividad reales (número de días únicos con eventos dentro de la ventana)
        dias_activos_7d = int(df_7d['solo_fecha'].nunique())
        dias_activos_30d = int(df_30d['solo_fecha'].nunique())
        
        max_hist_g = int(df_g['numero_lista'].max())
        
        gerencia_data = {
            "gerencia_id": str(g).upper().replace(" ", "_"),
            "nombre_gerencia": str(g),
            "fecha_ultimo_llamamiento": str(row_ult_g['fecha_dt']),
            "dias_desde_ultimo_llamamiento": dias_desde,
            "clasificacion_actividad": "Muy activa" if dias_desde <= 5 else "Estable / Lenta",
            "maximo_historico_alcanzado": max_hist_g,
            "consulta_periodos": {
                "ultimos_7_dias": {
                    "total_llamamientos": int(len(df_7d)),
                    "dias_con_actividad": dias_activos_7d,
                    "maximo_alcanzado": int(df_7d['numero_lista'].max()) if not df_7d.empty else 0
                },
                "ultimos_30_dias": {
                    "total_llamamientos": int(len(df_30d)),
                    "dias_con_actividad": dias_activos_30d,
                    "maximo_alcanzado": int(df_30d['numero_lista'].max()) if not df_30d.empty else 0
                },
                "historico_completo": {
                    "total_llamamientos": int(len(df_g)),
                    "maximo_historico": max_hist_g
                }
            }
        }
        gerencias_resultado.append(gerencia_data)
        
    # 3. Motor de consulta personalizada por Número de Lista (Funcionalidad Estrella)
    buscador_personalizado = None
    if numero_lista_usuario is not None:
        # Evaluar la situación del usuario frente a los máximos alcanzados en cada gerencia
        comparativa_gerencias = []
        for g_res in gerencias_resultado:
            max_alcanzado = g_res["maximo_historico_alcanzado"]
            distancia = numero_lista_usuario - max_alcanzado
            
            if distancia <= 0:
                estado_opositor = "Alcanzado / Superado"
            else:
                estado_opositor = f"A {distancia} puestos del máximo actual"
                
            comparativa_gerencias.append({
                "gerencia": g_res["nombre_gerencia"],
                "maximo_actual_gerencia": max_alcanzado,
                "distancia_puestos": distancia if distancia > 0 else 0,
                "estado": estado_opositor
            })
            
        buscador_personalizado = {
            "numero_consultado": int(numero_lista_usuario),
            "resultados_por_gerencia": comparativa_gerencias
        }

    # Salida final unificada
    observatorio_json = {
        "metadata": metadata,
        "buscador_personalizado": buscador_personalizado,
        "gerencias": gerencias_resultado
    }
    
    return observatorio_json
