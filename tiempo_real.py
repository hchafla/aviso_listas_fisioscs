import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import csv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL_WEB = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"

# ID de tu hoja de cálculo para el histórico estadístico
SPREADSHEET_ID = "1nmfP4nXQ4Oydvic_rZ1K19zCQBinAicHG38MeKUO0MU"

# Mapeo verificado con tus enlaces e hilos específicos del grupo de Fisioterapia
GERENCIAS_TOTALES = [
    {"nombre": "Lanzarote", "valor": "22", "thread_id": 98},
    {"nombre": "Fuerteventura", "valor": "23", "thread_id": 3},
    {"nombre": "CHUIMI", "valor": "24", "thread_id": 4},
    {"nombre": "Candelaria", "valor": "25", "thread_id": 5},
    {"nombre": "La Palma", "valor": "26", "thread_id": 6},
    {"nombre": "La Gomera", "valor": "27", "thread_id": 7},
    {"nombre": "El Hierro", "valor": "28", "thread_id": 8},
    {"nombre": "Atención Primaria Tenerife", "valor": "30", "thread_id": 9},
    {"nombre": "Atención Primaria Gran Canaria", "valor": "20", "thread_id": 10},
    {"nombre": "Dr. Negrín", "valor": "21", "thread_id": 12}
]

# Diccionario explícito para vincular el string 'valor' con su archivo CSV físico
MAPEO_CSV = {
    "20": "gapgc.csv",
    "21": "negrin.csv",
    "22": "lanzarote.csv",
    "23": "fuerteventura.csv",
    "24": "chuimi.csv",
    "25": "candelaria.csv",
    "26": "lapalma.csv",
    "27": "lagomera.csv",
    "28": "elhierro.csv",
    "30": "gaptf.csv"
}

def formatear_nombre(nombre_raw):
    """Transforma 'APELLIDOS, NOMBRE' a 'Nombre Apellidos' con formato Capitalizado."""
    if ',' not in nombre_raw:
        return nombre_raw.strip().title()
    
    apellidos, nombre = nombre_raw.split(',', 1)
    return f"{nombre.strip().title()} {apellidos.strip().title()}"

def buscar_nombre_en_csv(valor_gerencia, orden_gerencia):
    """Busca en el archivo CSV correspondiente el nombre por el campo orden_gerencia.
    Usa utf-8-sig para omitir el BOM generado por generar_csv.py."""
    nombre_archivo = MAPEO_CSV.get(str(valor_gerencia))
    if not nombre_archivo:
        return "Nombre no encontrado (actualizar listado)"
    
    ruta_csv = os.path.join("nombres", nombre_archivo)
    if not os.path.exists(ruta_csv):
        return "Nombre no encontrado (actualizar listado)"
    
    try:
        with open(ruta_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("orden_gerencia", "")).strip() == str(orden_gerencia).strip():
                    return formatear_nombre(row.get("nombre", ""))
    except Exception as e:
        print(f"Error leyendo {ruta_csv}: {e}")
        
    return "Nombre no encontrado (actualizar listado)"

def obtener_servicio_sheets():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("Error: No se encontró la variable de entorno GOOGLE_CREDENTIALS")
        return None
    try:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except Exception as e:
        print(f"Error al conectar con Google Sheets API: {e}")
        return None

def registrar_en_sheets(sheets_service, nombre_gerencia, tipo_lista, contrato, num_gerencia, num_global, fecha_actual):
    if not sheets_service:
        return
    
    try:
        num_g = int(num_gerencia)
    except ValueError:
        num_g = num_gerencia
        
    try:
        num_gl = int(num_global)
    except ValueError:
        num_gl = num_global

    valores = [[fecha_actual, nombre_gerencia, tipo_lista, contrato, num_g, num_gl]]
    cuerpo = {"values": valores}
    
    try:
        sheets_service.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Histórico_Datos!A:F",
            valueInputOption="USER_ENTERED",
            body=cuerpo
        ).execute()
        print(f"Fila registrada en Sheets para {nombre_gerencia} ({contrato})")
    except Exception as e:
        print(f"Error al escribir en Google Sheets: {e}")

def enviar_telegram(mensaje, thread_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": mensaje, 
        "parse_mode": "Markdown", 
        "disable_web_page_preview": True,
        "message_thread_id": thread_id
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code != 200:
            print(f"Error Telegram Fisio (Hilo {thread_id}): {response.text}")
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def procesar_gerencia(session, sheets_service, nombre, valor_gerencia, thread_id):
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    url_cat = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    
    fichero_estado = f"estado_{valor_gerencia}.txt"

    try:
        r_home = session.get(url_base, timeout=15)
        vs_1 = extraer_view_state(r_home.text)
        payload_g = {"j_idt43": "j_idt43", "j_idt43:gerenciaUNSOM_input": valor_gerencia, "j_idt43:j_idt46": "Seleccionar", "javax.faces.ViewState": vs_1}
        r_cat = session.post(url_base, data=payload_g, timeout=15)
        vs_2 = extraer_view_state(r_cat.text)
        payload_c = {"j_idt13": "j_idt13", "j_idt13:categoriasSOM_input": "97", "j_idt13:j_idt16": "Seleccionar", "javax.faces.ViewState": vs_2}
        r_final = session.post(url_cat, data=payload_c, timeout=15)
        
        soup = BeautifulSoup(r_final.text, "html.parser")
        filas = [f for f in soup.find_all("tr") if len(f.find_all("td")) >= 3 and any(kw in f.get_text() for kw in ["Corta", "Larga", "Interinidad"])]
        
        datos_actuales = ""
        lineas_ord, lineas_disc = [], []
        
        estado_ant = ""
        if os.path.exists(fichero_estado):
            with open(fichero_estado, "r") as f: 
                estado_ant = f.read().strip()

        for fila in filas:
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            info_linea = f"{celdas[0]}:{celdas[1]}-{celdas[2]}"
            datos_actuales += info_linea + "|"

        if datos_actuales != estado_ant:
            ahora = datetime.now()
            fecha_sheets = ahora.strftime("%Y-%m-%d %H:%M:%S")
            fecha_telegram = ahora.strftime("%d/%m/%Y - %H:%M")

            for idx, fila in enumerate(filas):
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                info_linea = f"{celdas[0]}:{celdas[1]}-{celdas[2]}"
                
                # Control de formato según si la línea concreta sufrió cambios
                if estado_ant and (info_linea not in estado_ant):
                    # LÍNEA MODIFICADA: Estilos de Markdown balanceados sin asteriscos huérfanos
                    nombre_aspirante = buscar_nombre_en_csv(valor_gerencia, celdas[1])
                    texto_linea = (
                        f"⚠️ *• {celdas[0]} ➔ Gerencia:* `{celdas[1]}` *| Global:* `{celdas[2]}`\n"
                        f"     👤 {nombre_aspirante}"
                    )
                    tipo_lista = "Ordinaria" if idx < 3 else "Discapacidad"
                    registrar_en_sheets(sheets_service, nombre, tipo_lista, celdas[0], celdas[1], celdas[2], fecha_sheets)
                else:
                    # LÍNEA SIN CAMBIOS: Mantiene el formato estándar original sin el nombre
                    texto_linea = f"  • {celdas[0]} ➔ Gerencia: {celdas[1]} | Global: {celdas[2]}"
                    if not estado_ant:
                        tipo_lista = "Ordinaria" if idx < 3 else "Discapacidad"
                        registrar_en_sheets(sheets_service, nombre, tipo_lista, celdas[0], celdas[1], celdas[2], fecha_sheets)
                
                if idx < 3: 
                    lineas_ord.append(texto_linea)
                else: 
                    lineas_disc.append(texto_linea)

            with open(fichero_estado, "w") as f: 
                f.write(datos_actuales)
            
            txt_ord = "\n".join(lineas_ord)
            txt_disc = "\n".join(lineas_disc)
            
            msg = f"🔄 *SCS: {nombre}*\n📅 _Actualizado: {fecha_telegram}_\n🏥 *Fisioterapeuta*\n\n📋 *Ordinarios:*\n{txt_ord}\n\n♿ *Discapacidad:*\n{txt_disc}\n\n🔗 [Ver en la web]({URL_WEB})"
            enviar_telegram(msg, thread_id)
            
    except Exception as e:
        print(f"Error en {nombre}: {e}")

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    sheets_service = obtener_servicio_sheets()
    for g in GERENCIAS_TOTALES:
        procesar_gerencia(session, sheets_service, g['nombre'], g['valor'], g['thread_id'])

if __name__ == "__main__":
    main()
