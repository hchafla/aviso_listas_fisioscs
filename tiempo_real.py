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
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    # 1. Cargar Home
    r_home = session.get(URL_BASE)
    vs_1 = extraer_view_state(r_home.text)
    
    # 2. Seleccionar Gerencia (Síncrono)
    payload_g = {
        "j_idt43": "j_idt43", 
        "j_idt43:gerenciaUNSOM_input": valor_gerencia, 
        "j_idt43:j_idt46": "Seleccionar", 
        "javax.faces.ViewState": vs_1
    }
    session.post(URL_BASE, data=payload_g)
    
    # 3. Navegar a Categorías (GET directo)
    # Al hacer GET, forzamos al servidor a darnos la página limpia con el formulario correcto
    r_cat = session.get(URL_CAT)
    vs_2 = extraer_view_state(r_cat.text)
    
    # 4. Seleccionar Categoría (Síncrono, no AJAX)
    payload_c = {
        "j_idt13": "j_idt13", 
        "j_idt13:categoriasSOM_input": "97", 
        "j_idt13:j_idt16": "Seleccionar", 
        "javax.faces.ViewState": vs_2
    }
    
    # Quitamos todas las cabeceras AJAX y hacemos un POST estándar
    r_final = session.post(URL_CAT, data=payload_c)
    
    # Validación
    soup = BeautifulSoup(r_final.text, "html.parser")
    if soup.find("form", id="j_idt13"):
        print(f"✅ ÉXITO: Formulario j_idt13 encontrado para {nombre}.")
    else:
        print(f"❌ FALLO: El servidor no devolvió el formulario. Posible sesión expirada.")

def main():
    gerencias = [{"nombre": "GAPGC", "valor": "20"}, {"nombre": "NEGRIN", "valor": "21"}]
    for g in gerencias:
        procesar_gerencia(g['nombre'], g['valor'])

if __name__ == "__main__":
    main()
