import os
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
URL_CAT = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def procesar_gerencia(nombre, valor_gerencia):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    # 1. Cargar Home para obtener sesión y primer ViewState
    r_home = session.get(URL_BASE)
    vs_1 = extraer_view_state(r_home.text)
    
    # 2. POST para seleccionar Gerencia
    payload_g = {
        "j_idt43": "j_idt43", 
        "j_idt43:gerenciaUNSOM_input": valor_gerencia, 
        "j_idt43:j_idt46": "Seleccionar", 
        "javax.faces.ViewState": vs_1
    }
    session.post(URL_BASE, data=payload_g)
    
    # 3. Obtener ViewState tras la selección de gerencia
    r_cat_init = session.get(URL_CAT)
    vs_2 = extraer_view_state(r_cat_init.text)
    
    # 4. POST para seleccionar Categoría (Fisioterapeuta = 97)
    # Se incluyen las cabeceras AJAX críticas que exige PrimeFaces
    payload_c = {
        "j_idt13": "j_idt13", 
        "j_idt13:categoriasSOM_input": "97", 
        "j_idt13:j_idt16": "Seleccionar", 
        "javax.faces.ViewState": vs_2,
        "javax.faces.source": "j_idt13:j_idt16",
        "javax.faces.partial.ajax": "true",
        "javax.faces.partial.execute": "j_idt13",
        "javax.faces.partial.render": "j_idt13",
        "javax.faces.behavior.event": "click"
    }
    
    headers_ajax = {
        "Faces-Request": "partial/ajax",
        "Referer": URL_CAT
    }
    
    r_final = session.post(URL_CAT, data=payload_c, headers=headers_ajax)
    
    # Validación del resultado
    soup = BeautifulSoup(r_final.text, "html.parser")
    if soup.find("form", id="j_idt13"):
        print(f"✅ ÉXITO: Formulario j_idt13 encontrado para {nombre}.")
    else:
        print(f"❌ ERROR: Formulario no encontrado en {nombre}. Verifica el ViewState o si la sesión fue rechazada.")

def main():
    # Lista reducida para prueba rápida
    gerencias = [{"nombre": "GAPGC
