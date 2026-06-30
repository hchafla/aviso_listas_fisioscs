import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import csv
import pdfplumber

# --- CONFIGURACIÓN ---
URL_BASE = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
URL_CAT = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def procesar_gerencia(nombre, valor_gerencia):
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    # 1. Cargar Home
    r_home = session.get(URL_BASE)
    vs_1 = extraer_view_state(r_home.text)
    
    # 2. Seleccionar Gerencia
    payload_g = {
        "j_idt43": "j_idt43", 
        "j_idt43:gerenciaUNSOM_input": valor_gerencia, 
        "j_idt43:j_idt46": "Seleccionar", 
        "javax.faces.ViewState": vs_1
    }
    r_cat = session.post(URL_BASE, data=payload_g)
    vs_2 = extraer_view_state(r_cat.text)
    
    # 3. Seleccionar Categoría (Fisioterapeuta = 97)
    # IMPORTANTE: Se añade el parámetro de evento 'javax.faces.behavior.event' 
    # y el nombre del componente para engañar al filtro de seguridad de PrimeFaces
    payload_c = {
        "j_idt13": "j_idt13", 
        "j_idt13:categoriasSOM_input": "97", 
        "j_idt13:j_idt16": "Seleccionar", 
        "javax.faces.ViewState": vs_2,
        "javax.faces.source": "j_idt13:j_idt16",
        "javax.faces.partial.event": "click",
        "javax.faces.partial.execute": "j_idt13",
        "javax.faces.partial.render": "j_idt13"
    }
    r_final = session.post(URL_CAT, data=payload_c)
    
    # 4. Debug: Si el formulario no aparece, imprimimos qué nos devolvió el servidor
    soup = BeautifulSoup(r_final.text, "html.parser")
    if not soup.find("form", id="j_idt13"):
        print(f"❌ ERROR: Formulario no encontrado en {nombre}. HTML recibido (inicio): {r_final.text[:200]}")
        return

    print(f"✅ Gerencia {nombre} procesada correctamente.")
    # ... resto de tu lógica de extracción de datos y descarga de PDF ...

def main():
    gerencias = [{"nombre": "GAPGC", "valor": "20"}, {"nombre": "NEGRIN", "valor": "21"}]
    for g in gerencias:
        procesar_gerencia(g['nombre'], g['valor'])

if __name__ == "__main__":
    main()
