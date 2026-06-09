import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL_WEB = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"

# ID de tu hoja de cálculo
SPREADSHEET_ID = "1nmfP4nXQ4Oydvic_rZ1K19zCQBinAicHG38MeKUO0MU"

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

def obtener_servicio_sheets():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("Error: No se encontró la variable de entorno GOOGLE_CREDENTIALS")
        return None
    try:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except Exception as e:
        print(f"Error al conectar con Google Sheets API: {e}")
        return None

def registrar_en_sheets(sheets_service, nombre_gerencia, tipo_lista, contrato, num_gerencia, num_global):
    if not sheets_service:
        return
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        num_g = int(num_gerencia)
    except ValueError:
        num_g = num_gerencia
        
    try:
        num_gl = int(num_global)
    except ValueError:
        num_gl = num_global

    valores = [[fecha_actual, nombre_gerencia, tipo_lista, contrato, num_g, num_gl]]
    cuerpo = {"values": valores}
    
    try:
        sheets_service.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Histórico_Datos!A:F",
            valueInputOption="USER_ENTERED",
            body=cuerpo
        ).execute()
        print(f"Fila registrada en Sheets para {nombre_gerencia} ({contrato})")
    except Exception as e:
        print(f"Error al escribir en Google Sheets: {e}")

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

def procesar_gerencia(session, sheets_service, nombre, valor_gerencia):
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
        
        estado_ant = ""
        if os.path.exists(fichero_estado):
            with open(fichero_estado, "r") as f: estado_ant = f.read().strip()

        for idx, fila in enumerate(filas):
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            info_linea = f"{celdas[0]}:{celdas[1]}-{celdas[2]}"
            datos_actuales += info_linea + "|"
            
            texto_linea = f"  • {celdas[0]} ➔ Gerencia: `{celdas[1]}` | Global: `{celdas[2]}`"
            
            if estado_ant and info_linea not in estado_ant:
                texto_linea = f"⚠️ {texto_linea}"
                tipo_lista = "Ordinaria" if idx < 3 else "Discapacidad"
                registrar_en_sheets(sheets_service, nombre, tipo_lista, celdas[0], celdas[1], celdas[2])
            
            if idx < 3: lineas_ord.append(texto_linea)
            else: lineas_disc.append(texto_linea)

        if datos_actuales != estado_ant:
            with open(fichero_estado, "w") as f: f.write(datos_actuales)
            
            txt_ord = "\n".join(lineas_ord)
            txt_disc = "\n".join(lineas_disc)
            
            msg = f"🔄 *SCS: {nombre}*\n🏥 _Fisioterapeuta_\n\n📋 *Ordinarios:*\n{txt_ord}\n\n♿ *Discapacidad:*\n{txt_disc}\n\n🔗 [Ver en la web]({URL_WEB})"
            enviar_telegram(msg)
            
    except Exception as e:
        print(f"Error en {nombre}: {e}")

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    sheets_service = obtener_servicio_sheets()
    for g in GERENCIAS_TOTALES:
        procesar_gerencia(session, sheets_service, g['nombre'], g['valor'])

if __name__ == "__main__":
    main()
