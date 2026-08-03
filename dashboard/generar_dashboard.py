from datetime import datetime, timedelta
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
        print("CSV descargado correctamente desde Google Sheets.")
        return True
    except Exception as e:
        print(f"Error al descargar el CSV desde Google Sheets: {e}")
        return False


def generar_dashboard():
    sheet_id = "1sHmB41ka-RyK-F04Chf7F40dirLO34Dhx2KmAYaV1W8"

    if not descargar_csv_de_sheets(sheet_id, "llamamientos.csv"):
        return

    archivo_csv = "llamamientos.csv"
    if not Path(archivo_csv).exists():
        print(f"No se encuentra el archivo {archivo_csv}")
        return

    df = pd.read_csv(archivo_csv, header=None)
    print(f"Total de filas leídas en bruto del CSV: {len(df)}")

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

    # Conversión de fechas
    df["FechaHora"] = pd.to_datetime(
        df["FechaHora"], format="mixed", errors="coerce"
    )
    print(
        f"Filas con fechas válidas tras conversión: {df['FechaHora'].notna().sum()}"
    )

    if df["FechaHora"].notna().sum() > 0:
        print(f"Fecha mínima en el CSV: {df['FechaHora'].min()}")
        print(f"Fecha máxima en el CSV: {df['FechaHora'].max()}")

    df = df.dropna(subset=["FechaHora"])
    df = df.sort_values("FechaHora", ascending=True)

    df["NumeroGerencia"] = pd.to_numeric(df["NumeroGerencia"], errors="coerce")

    ahora = datetime.now()
    print(f"Fecha/Hora actual del servidor (ahora): {ahora}")
    fecha_actualizacion = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Construir estado actual y ranking por gerencia
    estado_por_gerencia = {}
    ranking_list = []

    ultimos_registros = df.groupby("Gerencia").tail(1)
    print(
        f"Gerencias encontradas para el estado actual: {list(ultimos_registros['Gerencia'].unique())}"
    )

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

    # 3. Análisis temporal por ventanas de días
    ventanas = [7, 15, 30, 90, 180]
    metricas_por_ventana = {}

    for dias in ventanas:
        fecha_limite = ahora - timedelta(days=dias)
        df_ventana = df[df["FechaHora"] >= fecha_limite]
        print(f"Ventana de {dias} días (desde {fecha_limite}): {len(df_ventana)} registros encontrados")

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

    print(f"Total registros de evolución temporal generados: {len(evolucion_temporal)}")

    # 5. Estructura final del JSON
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
            "ventanas_dias": ventanas,
            "metricas_por_ventana": metricas_por_ventana,
        },
        "consulta_usuario": {
            "nota": "Estructura preparada para consultas de umbrales en frontend."
        },
        "evolucion_temporal": evolucion_temporal,
    }

    # 6. Guardar el archivo directamente en la carpeta actual (dashboard/)
    archivo_salida = "dashboard.json"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print(f"¡ {archivo_salida} generado con éxito!")


if __name__ == "__main__":
    generar_dashboard()
