import requests
import time
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": URL_BASE
    })

    # 1. Home
    r_home = session.get(URL_BASE)
    vs_1 = extraer_view_state(r_home.text)
    
    # 2. Selección Gerencia
    session.post(URL_BASE, data={
        "j_idt43": "j_idt43", 
        "j_idt43:gerenciaUNSOM_input": valor_gerencia, 
        "j_idt43:j_idt46": "Seleccionar", 
        "javax.faces.ViewState": vs_1
    })
    time.sleep(2) # Pausa de seguridad
    
    # 3. Preparación Categoría
    r_cat = session.get(URL_CAT)
    vs_2 = extraer_view_state(r_cat.text)
    session.post(URL_CAT, data={
        "j_idt13": "j_idt13", 
        "j_idt13:categoriasSOM_input": "97", 
        "j_idt13:j_idt16": "Seleccionar", 
        "javax.faces.ViewState": vs_2
    })
    time.sleep(2) # Pausa de seguridad
    
    # 4. DISPARO PDF (Navegación simulada)
    # Obtenemos el ViewState final tras el último POST
    r_final = session.get(URL_CAT)
    vs_final = extraer_view_state(r_final.text)
    
    # Este payload replica el onclick="mojarra.jsfcljs"
    payload_pdf = {
        "j_idt13": "j_idt13",
        "j_idt13:j_idt15": "j_idt13:j_idt15",
        "javax.faces.ViewState": vs_final
    }
    
    # Cabeceras estrictas para evitar bloqueo
    headers = {
        "Faces-Request": "partial/ajax",
        "Origin": "https://www3.gobiernodecanarias.org",
        "Referer": URL_CAT
    }
    
    r_pdf = session.post(URL_CAT, data=payload_pdf, headers=headers)
    
    # Si devuelve HTML, imprimimos el principio para diagnosticar el mensaje de error
    if "PDF" in r_pdf.headers.get('Content-Type', '') or r_pdf.status_code == 200:
        with open(f"resultado_{nombre}.pdf", "wb") as f:
            f.write(r_pdf.content)
        print(f"✅ ÉXITO: PDF descargado para {nombre}")
    else:
        print(f"❌ FALLO en {nombre}. Content-Type: {r_pdf.headers.get('Content-Type')}")
        print(f"DEBUG HTML: {r_pdf.text[:300]}")

def main():
    gerencias = [{"nombre": "GAPGC", "valor": "20"}, {"nombre": "NEGRIN", "valor": "21"}]
    for g in gerencias:
        procesar_gerencia(g['nombre'], g['valor'])

if __name__ == "__main__":
    main()
