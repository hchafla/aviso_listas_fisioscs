import json
from pathlib import Path
import pandas as pd


def descargar_csv_de_sheets(file_id, ruta_salida="llamamientos.csv"):
    try:
        url_descarga = (
            f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"
        )
        df = pd.read_csv(url_descarga)
        df.to_csv(ruta_salida, index=False)
        return True
    except Exception as e:
        print(f"Error al descargar el CSV: {e}")
        return False


def generar_dashboard():
    sheet_id = "1sHmB41ka-RyK-F04Chf7F40dirLO34Dhx2KmAYaV1W8"

    if not descargar_csv_de_sheets(sheet_id, "llamamientos.csv"):
        return

    archivo_csv = "llamamientos.csv"
    if not Path(archivo_csv).exists():
        return

    df = pd.read_csv(archivo_csv, header=None)

    if df.shape[1] >= 6:
        df = df.iloc[:, :6]
        df.columns = [
            "FechaHora",
            "Gerencia",
            "Lista",
            "TipoNombramiento",
            "NumeroGerencia",
            "Extra",
        ]
    else:
        df.columns = [
            "FechaHora",
            "Gerencia",
            "Lista",
            "TipoNombramiento",
            "NumeroGerencia",
        ][: df.shape[1]]

    # Parsear fechas de forma limpia
    df["FechaHora"] = pd.to_datetime(
        df["FechaHora"], dayfirst=True, errors="coerce"
    )
    df = df.dropna(subset=["FechaHora"])
    df = df.sort_values("FechaHora", ascending=True)

    if df.empty:
        print("Error: No hay registros con fechas válidas.")
        return

    df["NumeroGerencia"] = pd.to_numeric(df["NumeroGerencia"], errors="coerce")

    # La última actualización es simplemente la fecha del último registro del CSV
    fecha_actualizacion = df["FechaHora"].max().strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Estado actual y ranking por gerencia
    estado_por_gerencia = {}
    ranking_list = []
    ultimos_registros = df.groupby("Gerencia").tail(1)

    for _, row in ultimos_registros.iterrows():
        gerencia = row["Gerencia"]
        num_gerencia = (
            int(row["NumeroGerencia"])
            if pd.notna(row["NumeroGerencia"])
            else None
        )
        fecha_str = row["FechaHora"].strftime("%Y-%m-%dT%H:%M:%SZ")

        estado_por_gerencia[gerencia] = {
            "numero_gerencia": num_gerencia,
            "numero_general": None,
            "lista": row["Lista"],
            "tipo_nombramiento": row["TipoNombramiento"],
            "fecha_hora": fecha_str,
        }

    conteo_historico = df["Gerencia"].value_counts().to_dict()

    for gerencia, datos in estado_por_gerencia.items():
        ranking_list.append(
            {
                "gerencia": gerencia,
                "ultimo_numero": datos["numero_gerencia"],
                "fecha_hora": datos["fecha_hora"],
                "total_cambios_historico": conteo_historico.get(gerencia, 0),
            }
        )

    ranking_list = sorted(
        ranking_list, key=lambda x: x["ultimo_numero"] or 0, reverse=True
    )

    # 2. Análisis histórico completo (sin restricciones de días inventadas)
    maximos_gerencia = {}
    max_por_g = df.groupby("Gerencia")["NumeroGerencia"].max().to_dict()
    for g, val in max_por_g.items():
        if pd.notna(val):
            maximos_gerencia[g] = int(val)

    metricas_historicas = {
        "total_cambios": int(len(df)),
        "maximo_por_gerencia": maximos_gerencia,
    }

    # 3. Evolución temporal con todos los datos
    df["FechaSolo"] = df["FechaHora"].dt.strftime("%Y-%m-%d")
    df_evolucion = (
        df.groupby(["FechaSolo", "Gerencia", "TipoNombramiento", "Lista"])[
            "NumeroGerencia"
        ]
        .max()
        .reset_index()
    )

    evolucion_temporal = []
    for _, row in df_evolucion.iterrows():
        if pd.notna(row["NumeroGerencia"]):
            evolucion_temporal.append(
                {
                    "fecha": row["FechaSolo"],
                    "gerencia": row["Gerencia"],
                    "numero_gerencia": int(row["NumeroGerencia"]),
                    "tipo_nombramiento": row["TipoNombramiento"],
                    "lista": row["Lista"],
                }
            )

    # 4. Estructura JSON final
    dashboard_data = {
        "metadata": {
            "ultima_actualizacion": fecha_actualizacion,
            "categoria": "Fisioterapia",
            "fuente": "Servicio Canario de la Salud (SCS)",
        },
        "estado_actual": {
            "por_gerencia": estado_por_gerencia,
            "ranking": ranking_list,
        },
        "analisis_temporal": {
            "metricas_historicas": metricas_historicas,
        },
        "consulta_usuario": {
            "nota": "Estructura preparada para consultas de umbrales en frontend."
        },
        "evolucion_temporal": evolucion_temporal,
    }

    archivo_salida = "dashboard.json"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print(f"Dashboard generado correctamente con {len(estado_por_gerencia)} gerencias y {len(evolucion_temporal)} registros.")


if __name__ == "__main__":
    generar_dashboard()
