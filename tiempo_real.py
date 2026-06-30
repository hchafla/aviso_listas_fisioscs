import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_FISIO")
URL_WEB = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
SPREADSHEET_ID = "1nmfP4nXQ4Oydvic_rZ1K19zCQBinAicHG38MeKUO0MU"

GERENCIAS_TOTALES = [
    {"nombre": "Lanzarote", "valor": "22", "thread_id": 2},
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

def obtener_servicio_sheets():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json: return None
    try:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except: return None

def registrar_en_sheets(sheets_service, nombre_gerencia, tipo_lista, contrato, num_gerencia, num_global, fecha_actual):
    if not sheets_service: return
    valores = [[fecha_actual, nombre_gerencia, tipo_lista, contrato, num_gerencia, num_global]]
    try:
        sheets_service.values().append(spreadsheetId=SPREADSHEET_ID, range="Histórico_Datos!A:F", valueInputOption="USER_ENTERED", body={"values": valores}).execute()
    except: pass

def enviar_telegram(mensaje, thread_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown", "disable_web_page_preview": True, "message_thread_id": thread_id}
    try: requests.post(url, json=payload, timeout=15)
    except: pass

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def procesar_gerencia(session, sheets_service, nombre, valor_gerencia, thread_id):
    fichero_estado = f"estado_{valor_gerencia}.txt"
    try:
        r_home = session.get("https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml", timeout=15)
        vs_1 = extraer_view_state(r_home.text)
        session.post("https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml", data={"j_idt43": "j_idt43", "j_idt43:gerenciaUNSOM_input": valor_gerencia, "j_idt43:j_idt46": "Seleccionar", "javax.faces.ViewState": vs_1})
        
        vs_2 = extraer_view_state(session.get("https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml").text)
        r_final = session.post("https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml", data={"j_idt13": "j_idt13", "j_idt13:categoriasSOM_input": "97", "j_idt13:j_idt16": "Seleccionar", "javax.faces.ViewState": vs_2})
        
        soup = BeautifulSoup(r_final.text, "html.parser")
        filas = [f for f in soup.find_all("tr") if len(f.find_all("td")) >= 3 and any(kw in f.get_text() for kw in ["Corta", "Larga", "Interinidad"])]
        
        datos_actuales = "".join([f"{f.find_all('td')[0].get_text(strip=True)}:{f.find_all('td')[1].get_text(strip=True)}-{f.find_all('td')[2].get_text(strip=True)}|" for f in filas])
        estado_ant = ""
        if os.path.exists(fichero_estado):
            with open(fichero_estado, "r") as f: estado_ant = f.read().strip()
        
        if datos_actuales != estado_ant:
            ahora = datetime.now()
            for idx, fila in enumerate(filas):
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                info_linea = f"{celdas[0]}:{celdas[1]}-{celdas[2]}"
                if not estado_ant or (info_linea not in estado_ant):
                    tipo_lista = "Ordinaria" if idx < 3 else "Discapacidad"
                    registrar_en_sheets(sheets_service, nombre, tipo_lista, celdas[0], celdas[1], celdas[2], ahora.strftime("%Y-%m-%d %H:%M:%S"))
            
            with open(fichero_estado, "w") as f: f.write(datos_actuales)
            # Enviar mensaje Telegram aquí con el formato original
            enviar_telegram(f"🔄 *SCS: {nombre}* Actualizado.", thread_id)
    except: pass

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    service = obtener_servicio_sheets()
    for g in GERENCIAS_TOTALES:
        procesar_gerencia(session, service, g['nombre'], g['valor'], g['thread_id'])

if __name__ == "__main__":
    main()
