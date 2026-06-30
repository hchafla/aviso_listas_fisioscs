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
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    # 1. Home
    r_home = session.get(URL_BASE)
    vs_1 = extraer_view_state(r_home.text)
    
    # 2. Selección Gerencia
    session.post(URL_BASE, data={"j_idt43": "j_idt43", "j_idt43:gerenciaUNSOM_input": valor_gerencia, "j_idt43:j_idt46": "Seleccionar", "javax.faces.ViewState": vs_1})
    
    # 3. Selección Categoría (Prepara la tabla)
    r_cat = session.get(URL_CAT)
    vs_2 = extraer_view_state(r_cat.text)
    session.post(URL_CAT, data={"j_idt13": "j_idt13", "j_idt13:categoriasSOM_input": "97", "j_idt13:j_idt16": "Seleccionar", "javax.faces.ViewState": vs_2})
    
    # 4. DISPARO PDF (Simulando el onclick="mojarra.jsfcljs(...)")
    # Debemos enviar el ViewState actualizado tras el paso 3
    vs_3 = extraer_view_state(session.get(URL_CAT).text)
    
    payload_pdf = {
        "j_idt13": "j_idt13",
        "j_idt13:j_idt15": "j_idt13:j_idt15", # EL PARÁMETRO CLAVE DEL ONCLICK
        "javax.faces.ViewState": vs_3
    }
    
    r_pdf = session.post(URL_CAT, data=payload_pdf)
    
    if r_pdf.headers.get('Content-Type') == 'application/pdf':
        with open(f"resultado_{nombre}.pdf", "wb") as f:
            f.write(r_pdf.content)
        print(f"✅ ÉXITO: PDF descargado para {nombre}")
    else:
        print(f"❌ FALLO: El servidor no devolvió un PDF. Content-Type: {r_pdf.headers.get('Content-Type')}")

def main():
    gerencias = [{"nombre": "GAPGC", "valor": "20"}, {"nombre": "NEGRIN", "valor": "21"}]
    for g in gerencias:
        procesar_gerencia(g['nombre'], g['valor'])

if __name__ == "__main__":
    main()
