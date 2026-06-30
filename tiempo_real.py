import os
import requests
import csv
import pdfplumber
from bs4 import BeautifulSoup
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

URL_BASE = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
URL_CAT = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return vs.get("value") if vs else None

def actualizar_mapeo_pdf(session, valor_gerencia, csv_path):
    print(f"DEBUG: Intentando descargar PDF para {valor_gerencia}")
    r_cat = session.get(URL_CAT)
    vs = extraer_view_state(r_cat.text)
    payload = {"j_idt13": "j_idt13", "j_idt13:j_idt15": "j_idt13:j_idt15", "javax.faces.ViewState": vs}
    r_pdf = session.post(URL_CAT, data=payload)
    
    if r_pdf.status_code == 200 and b"%PDF" in r_pdf.content[:20]:
        with open("temp.pdf", "wb") as f: f.write(r_pdf.content)
        mapeo = {}
        with pdfplumber.open("temp.pdf") as pdf:
            for p in pdf.pages:
                for row in (p.extract_table() or []):
                    if row and len(row) >= 3 and str(row[0]).strip().isdigit():
                        mapeo[str(row[0]).strip()] = str(row[2]).strip()
        with open(csv_path, "w", encoding="utf-8") as f:
            csv.writer(f).writerows(mapeo.items())
        print(f"DEBUG: {csv_path} creado con {len(mapeo)} registros.")
        return mapeo
    return {}

def procesar_gerencia(nombre, valor, thread_id):
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    
    # Navegación
    vs1 = extraer_view_state(s.get(URL_BASE).text)
    s.post(URL_BASE, data={"j_idt43": "j_idt43", "j_idt43:gerenciaUNSOM_input": valor, "j_idt43:j_idt46": "Seleccionar", "javax.faces.ViewState": vs1})
    vs2 = extraer_view_state(s.get(URL_CAT).text)
    r_final = s.post(URL_CAT, data={"j_idt13": "j_idt13", "j_idt13:categoriasSOM_input": "97", "j_idt13:j_idt16": "Seleccionar", "javax.faces.ViewState": vs2})
    
    soup = BeautifulSoup(r_final.text, "html.parser")
    filas = [f for f in soup.find_all("tr") if len(f.find_all("td")) >= 3 and any(k in f.get_text() for k in ["Corta", "Larga", "Interinidad"])]
    
    if not filas: return
    
    # Forzar actualización si el archivo no existe
    csv_path = f"mapeo_fisio_{valor}.csv"
    if not os.path.exists(csv_path): actualizar_mapeo_pdf(s, valor, csv_path)
    
    datos = "".join([f"{f.find_all('td')[0].get_text()}:{f.find_all('td')[1].get_text()}" for f in filas])
    f_estado = f"estado_{valor}.txt"
    
    if not os.path.exists(f_estado) or open(f_estado).read() != datos:
        print(f"DEBUG: Cambio detectado en {nombre}. Guardando estado.")
        with open(f_estado, "w") as f: f.write(datos)

# ... (ejecutar procesar_gerencia en un bucle main) ...
