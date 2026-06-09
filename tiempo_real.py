import os
import requests
from bs4 import BeautifulSoup

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    if input_vs:
        return input_vs.get("value")
    return None

def auditar_segunda_pantalla():
    url = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Connection": "keep-alive"
    })

    try:
        # Paso 1: Petición GET para obtener las cookies y el ViewState inicial
        print("Accediendo a la página principal...")
        r_home = session.get(url, timeout=15)
        vs_1 = extraer_view_state(r_home.text)
        
        if not vs_1:
            print("Error: No se pudo extraer el ViewState inicial.")
            return

        # Paso 2: Petición POST con los parámetros reales del HTML analizado
        print("Enviando selección de Gerencia (Hospital Negrín - Valor 21)...")
        payload_gerencia = {
            "j_idt43": "j_idt43",
            "j_idt43:gerenciaUNSOM_input": "21",
            "j_idt43:gerenciaUNSOM_focus": "",
            "j_idt43:j_idt46": "Seleccionar",  # ID real del botón según el código fuente
            "javax.faces.ViewState": vs_1
        }
        
        r_categorias = session.post(url, data=payload_gerencia, timeout=15)
        
        # Paso 3: Guardar el HTML de la segunda pantalla para analizar sus IDs
        print("Guardando el código fuente de la pantalla de categorías (pantalla_2.txt)...")
        with open("pantalla_2.txt", "w", encoding="utf-8") as f:
            f.write(r_categorias.text)
            
        print("Auditoría intermedia completada con éxito.")

    except Exception as e:
        print(f"Error durante la conexión directa: {e}")

if __name__ == "__main__":
    auditar_segunda_pantalla()
