import requests
from bs4 import BeautifulSoup

def listar_gerencias():
    url = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    session = requests.Session()
    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Buscamos el desplegable de gerencias
    select = soup.find("select", {"id": "j_idt43:gerenciaUNSOM_input"})
    
    if select:
        print("--- CÓDIGOS DE GERENCIA ENCONTRADOS ---")
        for option in select.find_all("option"):
            # Omitimos el valor vacío que es el texto de "Seleccione..."
            if option.get("value"):
                print(f"Gerencia: {option.text.strip()} | Valor: {option.get('value')}")
    else:
        print("No se encontró el desplegable. Revisa el selector.")

if __name__ == "__main__":
    listar_gerencias()
