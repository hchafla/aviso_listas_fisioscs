from datetime import datetime, timedelta
import json
from pathlib import Path
import pandas as pd


def descargar_csv_de_sheets(
    file_id, ruta_salida="llamamientos.csv"
):
    """Descarga el contenido de un Google Spreadsheet directamente en formato CSV."""
    try:
        url_descarga = (
            f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"
        )
        df = pd.read_csv(url_descarga)
        df.to_csv(ruta_salida, index=False)
        print("CSV descargado correctamente desde Google Sheets.")
        return True
    except Exception as e:
        print(f"Error al descargar el CSV desde Google Sheets: {e}")
        return False


def generar_dashboard():
    # ID de tu Google Sheets extraído del enlace proporcionado
    sheet_id = "1sHmB41ka-RyK-F04Chf7F40dirLO34Dhx2KmAYaV1W8"

    # 1. Descargar y cargar los datos
    if not descargar_csv_de_sheets(sheet_id, "llamamientos.csv"):
        return

    archivo_csv = "llamamientos.csv"
    if not Path(archivo_csv).exists():
        print(f"No se encuentra el archivo {archivo_csv}")
        return

    df = pd.read_csv(archivo_csv)

    # Limpieza básica y conversión de fechas
    df["FechaHora"] = pd.to_datetime(df["FechaHora"])
    df = df.sort_values("FechaHora", ascending=True)

    # Reemplazar valores nulos o "-" en los números por NaN
    df["NumeroGerencia"] = pd.to_numeric(df["NumeroGerencia"], errors="coerce")

    ahora = datetime.now()
    fecha_actualizacion = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Construir estado actual y ranking por gerencia
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
        fecha_str = (
            row["FechaHora"].strftime("%Y-%m-%dT%H:%M:%SZ")
            if pd.notna(row["FechaHora"])
            else fecha_actualizacion
        )

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

    # 3. Análisis temporal por ventanas de días (7, 15, 30, 90, 180)
    ventanas = [7, 15, 30, 90, 180]
    metricas_por_ventana = {}

    for dias in ventanas:
        fecha_limite = ahora - timedelta(days=dias)
        df_ventana = df[df["FechaHora"] >= fecha_limite]

        maximos_gerencia = {}
        if not df_ventana.empty:
            max_por_g = (
                df_ventana.groupby("Gerencia")["NumeroGerencia"]
                .max()
                .to_dict()
            )
            for g, val in max_por_g.items():
                if pd.notna(val):
                    maximos_gerencia[g] = int(val)

        metricas_por_ventana[str(dias)] = {
            "total_cambios": int(len(df_ventana)),
            "maximo_por_gerencia": maximos_gerencia,
        }

    # 4. Evolución temporal
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

    # 5. Estructura final del JSON
    dashboard_data = {
        "$schema": "https://testonlineope.es/schemas/dashboard-v1.json",
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
            "ventanas_dias": ventanas,
            "metricas_por_ventana": metricas_por_ventana,
        },
        "consulta_usuario": {
            "nota": "Estructura preparada para consultas de umbrales en frontend."
        },
        "evolucion_temporal": evolucion_temporal,
    }

    # 6. Guardar el archivo dashboard.json
    archivo_salida = "dashboard.json"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print(f"¡ {archivo_salida} generado con éxito!")


if __name__ == "__main__":
    generar_dashboard()
