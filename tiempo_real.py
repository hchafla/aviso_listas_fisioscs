import os
import requests
import csv
import pdfplumber
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_FISIO")
URL_BASE = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
URL_CAT = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
SPREADSHEET_ID = "1nmfP4nXQ4Oydvic_rZ1K19zCQBinAicHG38MeKUO0MU"

GERENCIAS_TOTALES = [
    {"nombre": "Lanzarote", "valor": "22", "thread_id": 2},
    {"nombre": "Fuerteventura", "valor": "23", "thread_id": 3},
    {"nombre": "CHUIMI", "valor": "24", "thread_id": 4},
    {"nombre": "Candelaria", "valor": "25", "thread_id": 5},
    {"nombre": "La Palma", "valor": "26", "thread_id": 6},
    {"nombre": "La Gomera", "valor": "27", "thread_id": 7},
    {"nombre": "El Hierro", "valor": "28", "thread_id": 8},
    {"nombre": "GAPTF", "valor": "30", "thread_id": 9},
    {"nombre": "GAPGC", "valor": "20", "thread_id": 10},
    {"nombre": "NEGRIN", "valor": "21", "thread_id": 12}
]

def obtener_servicio_sheets():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json: return None
    try:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except: return None

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def actualizar_mapeo_pdf(session, valor_gerencia, csv_path):
    print(f"⌛ Descargando nuevo PDF para {valor_gerencia}...")
    r_cat = session.get(URL_CAT)
    vs_final = extraer_view_state(r_cat.text)
    payload_pdf = {"j_idt13": "j_idt13", "j_idt13:j_idt15": "j_idt13:j_idt15", "javax.faces.ViewState": vs_final}
    r_pdf = session.post(URL_CAT, data=payload_pdf)
    
    mapeo = {}
    if r_pdf.status_code == 200 and b"%PDF" in r_pdf.content[:20]:
        pdf_temp = f"temp_{valor_gerencia}.pdf"
        with open(pdf_temp, "wb") as f: f.write(r_pdf.content)
        with pdfplumber.open(pdf_temp) as pdf:
            for pagina in pdf.pages:
                tabla = pagina.extract_table()
                if tabla:
                    for fila in tabla:
                        if fila and len(fila) >= 3 and str(fila[0]).strip().isdigit():
                            mapeo[str(fila[0]).strip()] = str(fila[2]).strip()
        if mapeo:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for k, v in mapeo.items(): writer.writerow([k, v])
        if os.path.exists(pdf_temp): os.remove(pdf_temp)
    return mapeo

def cargar_mapeo_nombres(session, valor_gerencia, csv_path):
    if os.path.exists(csv_path) and (datetime.now() - datetime.fromtimestamp(os.path.getmtime(csv_path)) < timedelta(days=7)):
        mapeo = {}
        with open(csv_path, "r", encoding="utf-8") as f:
            for fila in csv.reader(f):
                if len(fila) == 2: mapeo[fila[0]] = fila[1]
        return mapeo
    return actualizar_mapeo_pdf(session, valor_gerencia, csv_path)

def enviar_telegram(mensaje, thread_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown", "message_thread_id": int(thread_id)}
    requests.post(url, json=payload, timeout=15)

def procesar_gerencia(sheets_service, nombre, valor_gerencia, thread_id):
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    
    try:
        vs_1 = extraer_view_state(session.get(URL_BASE).text)
        session.post(URL_BASE, data={"j_idt43": "j_idt43", "j_idt43:gerenciaUNSOM_input": valor_gerencia, "j_idt43:j_idt46": "Seleccionar", "javax.faces.ViewState": vs_1})
        
        vs_2 = extraer_view_state(session.get(URL_CAT).text)
        r_final = session.post(URL_CAT, data={"j_idt13": "j_idt13", "j_idt13:categoriasSOM_input": "97", "j_idt13:j_idt16": "Seleccionar", "javax.faces.ViewState": vs_2})
        
        soup = BeautifulSoup(r_final.text, "html.parser")
        filas = [f for f in soup.find_all("tr") if len(f.find_all("td")) >= 3 and any(kw in f.get_text() for kw in ["Corta", "Larga", "Interinidad"])]
        
        if not filas: return 

        datos_actuales = "".join([f"{f.find_all('td')[0].get_text(strip=True)}:{f.find_all('td')[1].get_text(strip=True)}-{f.find_all('td')[2].get_text(strip=True)}" for f in filas])
        fichero_estado = f"estado_{valor_gerencia}.txt"
        
        estado_ant = ""
        if os.path.exists(fichero_estado):
            with open(fichero_estado, "r") as f: estado_ant = f.read().strip()
        
        if datos_actuales != estado_ant and estado_ant != "":
            mapa_nombres = cargar_mapeo_nombres(session, valor_gerencia, f"mapeo_fisio_{valor_gerencia}.csv")
            lineas_ord, lineas_disc = [], []
            for idx, fila in enumerate(filas):
                c = [td.get_text(strip=True) for td in fila.find_all("td")]
                nombre_p = mapa_nombres.get(c[1], "Nombre no disponible")
                texto = f"  • {c[0]} ➔ Gerencia: `{c[1]}` (*{nombre_p}*) | Global: `{c[2]}`"
                if idx < 3: lineas_ord.append(texto)
                else: lineas_disc.append(texto)
            
            msg = f"🔄 *SCS: {nombre}*\n\n📋 *Ordinarios:*\n" + "\n".join(lineas_ord) + "\n\n👑 *Discapacidad:*\n" + "\n".join(lineas_disc)
            enviar_telegram(msg, thread_id)
            with open(fichero_estado, "w") as f: f.write(datos_actuales)
        elif estado_ant == "":
            with open(fichero_estado, "w") as f: f.write(datos_actuales)
    except Exception as e: print(f"Error en {nombre}: {e}")

def main():
    service = obtener_servicio_sheets()
    for g in GERENCIAS_TOTALES:
        try: procesar_gerencia(service, g['nombre'], g['valor'], g['thread_id'])
        except Exception as e: print(f"Error {g['nombre']}: {e}")

if __name__ == "__main__":
    main()
