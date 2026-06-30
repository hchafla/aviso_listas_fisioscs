import requests
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning

# Ignorar aviso de parser
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

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
    session.post(URL_BASE, data=payload_g)
    
    # 3. Obtener ViewState de la página de categorías
    r_cat_init = session.get(URL_CAT)
    vs_2 = extraer_view_state(r_cat_init.text)
    
    # 4. POST AJAX para seleccionar Categoría
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
    
    # --- DEPURACIÓN A TIRO HECHO ---
    if "<partial-response" in r_final.text:
        print(f"✅ Respuesta AJAX recibida para {nombre}.")
        if 'id="j_idt13"' in r_final.text:
            print(f"✅ ÉXITO: El formulario j_idt13 está dentro del XML.")
        else:
            print(f"❌ ERROR: El formulario no aparece en el XML de respuesta.")
            print(f"DEBUG XML (primeros 500 chars): {r_final.text[:500]}")
    else:
        print(f"❌ ERROR: No es una respuesta XML. Servidor respondió: {r_final.text[:200]}")

def main():
    gerencias = [
        {"nombre": "GAPGC", "valor": "20"}, 
        {"nombre": "NEGRIN", "valor": "21"}
    ]
    for g in gerencias:
        procesar_gerencia(g['nombre'], g['valor'])

if __name__ == "__main__":
    main()
