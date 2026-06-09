import os
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL_WEB = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"

GERENCIAS_TOTALES = [
    {"nombre": "Lanzarote", "valor": "22"},
    {"nombre": "Fuerteventura", "valor": "23"},
    {"nombre": "CHUIMI", "valor": "24"},
    {"nombre": "Candelaria", "valor": "25"},
    {"nombre": "La Palma", "valor": "26"},
    {"nombre": "La Gomera", "valor": "27"},
    {"nombre": "El Hierro", "valor": "28"},
    {"nombre": "Atención Primaria Tenerife", "valor": "30"},
    {"nombre": "Atención Primaria Gran Canaria", "valor": "20"},
    {"nombre": "Dr. Negrín", "valor": "21"}
]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload, timeout=15)

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def procesar_gerencia(session, nombre, valor_gerencia):
    fichero_estado = f"estado_{valor_gerencia}.txt"
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    url_cat = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"

    try:
        r_home = session.get(url_base, timeout=15)
        vs_1 = extraer_view_state(r_home.text)
        payload_g = {"j_idt43": "j_idt43", "j_idt43:gerenciaUNSOM_input": valor_gerencia, "j_idt43:j_idt46": "Seleccionar", "javax.faces.ViewState": vs_1}
        r_cat = session.post(url_base, data=payload_g, timeout=15)
        vs_2 = extraer_view_state(r_cat.text)
        payload_c = {"j_idt13": "j_idt13", "j_idt13:categoriasSOM_input": "97", "j_idt13:j_idt16": "Seleccionar", "javax.faces.ViewState": vs_2}
        r_final = session.post(url_cat, data=payload_c, timeout=15)
        
        soup = BeautifulSoup(r_final.text, "html.parser")
        filas = [f for f in soup.find_all("tr") if len(f.find_all("td")) >= 3 and any(kw in f.get_text() for kw in ["Corta", "Larga", "Interinidad"])]
        
        datos_actuales = ""
        lineas_formateadas = []
        estado_ant = {}
        
        # Cargar estado previo
        if os.path.exists(fichero_estado):
            with open(fichero_estado, "r") as f:
                contenido = f.read().strip()
                if contenido:
                    for l in contenido.split("|"):
                        if ":" in l: estado_ant[l.split(":")[0]] = l.split(":")[1]

        # Procesar filas
        for f in filas:
            celdas = [c.get_text(strip=True) for c in f.find_all("td")]
            key, val = celdas[0], f"{celdas[1]}-{celdas[2]}"
            datos_actuales += f"{key}:{val}|"
            
            linea = f"  • {key} ➔ Gerencia: {celdas[1]} | Global: {celdas[2]}"
            # Poner en negrita si es un cambio o si es primera ejecución (estado_ant vacío)
            if estado_ant and estado_ant.get(key) != val:
                linea = f"**{linea}**"
            lineas_formateadas.append(linea)

        # Decidir si notificar
        es_primera_vez = not os.path.exists(fichero_estado)
        if datos_actuales != "|".join([f"{k}:{v}" for k,v in estado_ant.items()]) + "|" or es_primera_vez:
            with open(fichero_estado, "w") as f: f.write(datos_actuales)
            titulo = "✅ *INICIALIZADO*" if es_primera_vez else "🔄 *CAMBIO DETECTADO*"
            msg = f"{titulo}: {nombre}\n🔗 [Ver en la web]({URL_WEB})\n\n" + "\n".join(lineas_formateadas)
            enviar_telegram(msg)
            
    except Exception as e:
        print(f"Error procesando {nombre}: {e}")

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    for g in GERENCIAS_TOTALES:
        procesar_gerencia(session, g['nombre'], g['valor'])

if __name__ == "__main__":
    main()
