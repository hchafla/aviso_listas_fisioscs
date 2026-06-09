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
    requests.post(url, json=payload)

def procesar_gerencia(session, nombre, valor_gerencia):
    fichero_estado = f"estado_{valor_gerencia}.txt"
    # ... (Lógica de requests igual a la anterior) ...
    # Supongamos que ya obtuviste 'filas' como lista de tuplas (tipo, pos_gerencia, pos_global)
    
    datos_actuales = ""
    lineas_formateadas = []
    estado_ant = {} # Diccionario para comparar línea a línea
    if os.path.exists(fichero_estado):
        with open(fichero_estado, "r") as f:
            for l in f.read().split("|"):
                if ":" in l: estado_ant[l.split(":")[0]] = l.split(":")[1]

    for f in filas:
        celdas = [c.get_text(strip=True) for c in f.find_all("td")]
        key = celdas[0]
        val = f"{celdas[1]}-{celdas[2]}"
        datos_actuales += f"{key}:{val}|"
        
        # Si la posición cambió respecto al estado anterior, ponemos negrita
        linea = f"  • {key} ➔ Gerencia: {celdas[1]} | Global: {celdas[2]}"
        if estado_ant.get(key) != val:
            linea = f"**{linea}**"
        lineas_formateadas.append(linea)

    if datos_actuales != "|".join([f"{k}:{v}" for k,v in estado_ant.items()]) + "|":
        with open(fichero_estado, "w") as f: f.write(datos_actuales)
        msg = f"🔄 *Cambios en: {nombre}*\n🔗 [Ver en la web]({URL_WEB})\n\n" + "\n".join(lineas_formateadas)
        enviar_telegram(msg)
