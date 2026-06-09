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
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def procesar_gerencia(session, nombre, valor_gerencia):
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    url_cat = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    fichero_estado = f"estado_{valor_gerencia}.txt"

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
        lineas_ord, lineas_disc = [], []
        
        # Cargar estado anterior para comparar
        estado_ant = ""
        if os.path.exists(fichero_estado):
            with open(fichero_estado, "r") as f: estado_ant = f.read().strip()

        for idx, fila in enumerate(filas):
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            info_linea = f"{celdas[0]}:{celdas[1]}-{celdas[2]}"
            datos_actuales += info_linea + "|"
            
            # Formato de línea
            texto_linea = f"  • {celdas[0]} ➔ Gerencia: `{celdas[1]}` | Global: `{celdas[2]}`"
            
            # Aplicar negrita si la línea cambió respecto al estado anterior
            if estado_ant and info_linea not in estado_ant:
                texto_linea = f"**{texto_linea}**"
            
            if idx < 3: lineas_ord.append(texto_linea)
            else: lineas_disc.append(texto_linea)

        if datos_actuales != estado_ant:
            with open(fichero_estado, "w") as f: f.write(datos_actuales)
            msg = f"🔄 *SCS: {nombre}*\n🔗 [Ver en la web]({URL_WEB})\n\n📋 *Ordinarios:*\n" + "\n".join(lineas_ord) + "\n\n♿ *Discapacidad:*\n" + "\n".join(lineas_disc)
            enviar_telegram(msg)
            
    except Exception as e:
        print(f"Error en {nombre}: {e}")

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    for g in GERENCIAS_TOTALES:
        procesar_gerencia(session, g['nombre'], g['valor'])

if __name__ == "__main__":
    main()
