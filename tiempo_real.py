import os
import requests
from bs4 import BeautifulSoup
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_FISIO")
URL_BASE = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
URL_CAT = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"

def obtener_servicio_sheets():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json: return None
    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds).spreadsheets()

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def procesar_gerencia(sheets_service, nombre, valor_gerencia, thread_id):
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    
    # Navegación inicial
    vs_1 = extraer_view_state(session.get(URL_BASE).text)
    session.post(URL_BASE, data={"j_idt43": "j_idt43", "j_idt43:gerenciaUNSOM_input": valor_gerencia, "j_idt43:j_idt46": "Seleccionar", "javax.faces.ViewState": vs_1})
    
    vs_2 = extraer_view_state(session.get(URL_CAT).text)
    r_final = session.post(URL_CAT, data={"j_idt13": "j_idt13", "j_idt13:categoriasSOM_input": "97", "j_idt13:j_idt16": "Seleccionar", "javax.faces.ViewState": vs_2})
    
    soup = BeautifulSoup(r_final.text, "html.parser")
    filas = [f for f in soup.find_all("tr") if len(f.find_all("td")) >= 3 and any(kw in f.get_text() for kw in ["Corta", "Larga", "Interinidad"])]
    
    datos_actuales = "".join([f"{f.find_all('td')[0].get_text(strip=True)}:{f.find_all('td')[1].get_text(strip=True)}-{f.find_all('td')[2].get_text(strip=True)}" for f in filas])
    fichero_estado = f"estado_{valor_gerencia}.txt"
    
    estado_ant = ""
    if os.path.exists(fichero_estado):
        with open(fichero_estado, "r") as f: estado_ant = f.read().strip()
        
    if datos_actuales != estado_ant:
        # Lógica de notificación a Telegram y Sheets
        with open(fichero_estado, "w") as f: f.write(datos_actuales)

def main():
    service = obtener_servicio_sheets()
    # Lista de gerencias...
    # procesar_gerencia(service, ...)

if __name__ == "__main__":
    main()
