import os
import requests
import csv
import pdfplumber
import time
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

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def actualizar_mapeo_pdf(session, valor_gerencia, csv_path):
    print(f"⌛ Descargando nuevo PDF para {valor_gerencia}...")
    r_cat = session.get(URL_CAT)
    vs_final = extraer_view_state(r_cat.text)
    payload = {"j_idt13": "j_idt13", "j_idt13:j_idt15": "j_idt13:j_idt15", "javax.faces.ViewState": vs_final}
    r_pdf = session.post(URL_CAT, data=payload)
    
    if r_pdf.status_code == 200 and b"%PDF" in r_pdf.content[:20]:
        pdf_temp = f"temp_{valor_gerencia}.pdf"
        with open(pdf_temp, "wb") as f: f.write(r_pdf.content)
        mapeo = {}
        with pdfplumber.open(pdf_temp) as pdf:
            for p in pdf.pages:
                tabla = p.extract_table()
                if tabla:
                    for f in tabla:
                        if f and len(f) >= 3 and str(f[0]).strip().isdigit():
                            mapeo[str(f[0]).strip()] = str(f[2]).strip()
        if mapeo:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for k, v in mapeo.items(): writer.writerow([k, v])
                f.flush()
                os.fsync(f.fileno()) # Fuerza la escritura real en disco
        if os.path.exists(pdf_temp): os.remove(pdf_temp)
        return mapeo
    return {}

def procesar_gerencia(nombre, valor_gerencia, thread_id):
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

        datos = "".join([f"{f.find_all('td')[0].get_text(strip=True)}:{f.find_all('td')[1].get_text(strip=True)}-{f.find_all('td')[2].get_text(strip=True)}" for f in filas])
        f_estado = f"estado_{valor_gerencia}.txt"
        
        # Carga forzada de CSV si es viejo
        csv_p = f"mapeo_fisio_{valor_gerencia}.csv"
        if not os.path.exists(csv_p) or (datetime.now() - datetime.fromtimestamp(os.path.getmtime(csv_p)) > timedelta(days=7)):
            actualizar_mapeo_pdf(session, valor_gerencia, csv_p)
        
        # Comparación
        estado_ant = ""
        if os.path.exists(f_estado):
            with open(f_estado, "r") as f: estado_ant = f.read().strip()
            
        if datos != estado_ant and estado_ant != "":
            # Recargar mapa actualizado
            mapa = {}
            with open(csv_p, "r", encoding="utf-8") as f:
                for row in csv.reader(f): mapa[row[0]] = row[1]
            
            # ... [Aquí tu lógica de mensaje Telegram] ...
            with open(f_estado, "w") as f: f.write(datos)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e: print(f"Error {nombre}: {e}")

# ... (main que llama a procesar_gerencia)
