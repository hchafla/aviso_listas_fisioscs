import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import csv
import pdfplumber
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_FISIO")
URL_WEB = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
SPREADSHEET_ID = "1nmfP4nXQ4Oydvic_rZ1K19zCQBinAicHG38MeKUO0MU"

GERENCIAS_TOTALES = [
    {"nombre": "Lanzarote", "valor": "22", "thread_id": 2},
    {"nombre": "Fuerteventura", "valor": "23", "thread_id": 3},
    {"nombre": "CHUIMI", "valor": "24", "thread_id": 4},
    {"nombre": "Candelaria", "valor": "25", "thread_id": 5},
    {"nombre": "La Palma", "valor": "26", "thread_id": 6},
    {"nombre": "La Gomera", "valor": "27", "thread_id": 7},
    {"nombre": "El Hierro", "valor": "28", "thread_id": 8},
    {"nombre": "GAPTF", "valor": "30", "thread_id": 9},
    {"nombre": "GAPGC", "valor": "20", "thread_id": 10},
    {"nombre": "NEGRIN", "valor": "21", "thread_id": 12}
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

def registrar_en_sheets(sheets_service, nombre_gerencia, tipo_lista, contrato, num_gerencia, num_global, fecha_actual):
    if not sheets_service:
        return
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

def enviar_telegram(mensaje, thread_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": mensaje, 
        "parse_mode": "Markdown", 
        "disable_web_page_preview": True,
        "message_thread_id": int(thread_id)
    }
    
    print(f"DEBUG Telegram Payload enviado: chat_id={TELEGRAM_CHAT_ID}, thread_id={thread_id}")
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code != 200:
            print(f"Error Telegram Fisio (Hilo {thread_id}): {response.text}")
        else:
            print(f"✅ Mensaje enviado correctamente al hilo {thread_id}")
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    return input_vs.get("value") if input_vs else None

def actualizar_mapeo_pdf(session, valor_gerencia, vs_actual, csv_path):
    print(f"⌛ Descargando y procesando PDF de aspirantes para gerencia {valor_gerencia}...")
    url_cat = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    
    payload_pdf = {
        "j_idt13": "j_idt13",
        "j_idt13:categoriasSOM_input": "97",
        "j_idt13:j_idt15": "j_idt13:j_idt15",
        "javax.faces.ViewState": vs_actual
    }
    
    try:
        r_pdf = session.post(url_cat, data=payload_pdf, timeout=45)
        if r_pdf.status_code != 200 or b"%PDF" not in r_pdf.content[:10]:
            print(f"❌ No se pudo obtener un PDF válido del SCS para la gerencia {valor_gerencia}")
            return {}

        pdf_temp = f"temp_{valor_gerencia}.pdf"
        with open(pdf_temp, "wb") as f:
            f.write(r_pdf.content)

        mapeo = {}
        with pdfplumber.open(pdf_temp) as pdf:
            for pagina in pdf.pages:
                tabla = pagina.extract_table()
                if not tabla:
                    continue
                for fila in tabla:
                    if not fila or len(fila) < 3 or "Orden" in str(fila[0]):
                        continue
                    orden_gerencia = str(fila[0]).strip()
                    nombre_aspirante = str(fila[2]).strip()
                    if orden_gerencia.isdigit():
                        mapeo[orden_gerencia] = nombre_aspirante

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for k, v in mapeo.items():
                writer.writerow([k, v])
                
        if os.path.exists(pdf_temp):
            os.remove(pdf_temp)
            
        print(f"✅ Archivo de caché creado con éxito: {len(mapeo)} nombres indexados.")
        return mapeo
    except Exception as e:
        print(f"Error crítico al procesar PDF de la gerencia {valor_gerencia}: {e}")
        return {}

def cargar_mapeo_nombres(session, valor_gerencia, vs_final, csv_path):
    if os.path.exists(csv_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(csv_path))
        if datetime.now() - mtime < timedelta(days=7):
            mapeo = {}
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for fila in reader:
                    if len(fila) == 2:
                        mapeo[fila[0]] = fila[1]
            return mapeo
    return actualizar_mapeo_pdf(session, valor_gerencia, vs_final, csv_path)

def procesar_gerencia(sheets_service, nombre, valor_gerencia, thread_id):
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    url_cat = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    
    fichero_estado = f"estado_{valor_gerencia}.txt"
    csv_path = f"mapeo_fisio_{valor_gerencia}.csv"

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    try:
        r_home = session.get(url_base, timeout=15)
        vs_1 = extraer_view_state(r_home.text)
        
        payload_g = {"j_idt43": "j_idt43", "j_idt43:gerenciaUNSOM_input": valor_gerencia, "j_idt43:j_idt46": "Seleccionar", "javax.faces.ViewState": vs_1}
        r_cat = session.post(url_base, data=payload_g, timeout=15)
        vs_2 = extraer_view_state(r_cat.text)
        
        payload_c = {"j_idt13": "j_idt13", "j_idt13:categoriasSOM_input": "97", "j_idt13:j_idt16": "Seleccionar", "javax.faces.ViewState": vs_2}
        r_final = session.post(url_cat, data=payload_c, timeout=15)
        vs_final = extraer_view_state(r_final.text)
        
        soup = BeautifulSoup(r_final.text, "html.parser")
        filas = [f for f in soup.find_all("tr") if len(f.find_all("td")) >= 3 and any(kw in f.get_text() for kw in ["Corta", "Larga", "Interinidad"])]
        
        datos_actuales = ""
        lineas_ord, lineas_disc = [], []
        
        estado_ant = ""
        if os.path.exists(fichero_estado):
            with open(fichero_estado, "r") as f: 
                estado_ant = f.read().strip()

        for fila in filas:
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            info_linea = f"{celdas[0]}:{celdas[1]}-{celdas[2]}"
            datos_actuales += info_linea + "|"

        if datos_actuales != estado_ant:
            ahora = datetime.now(ZoneInfo("Atlantic/Canary"))
            fecha_sheets = ahora.strftime("%Y-%m-%d %H:%M:%S")
            fecha_telegram = ahora.strftime("%d/%m/%Y - %H:%M")

            mapa_nombres = cargar_mapeo_nombres(session, valor_gerencia, vs_final, csv_path)

            for idx, fila in enumerate(filas):
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                info_linea = f"{celdas[0]}:{celdas[1]}-{celdas[2]}"
                
                nombre_persona = mapa_nombres.get(celdas[1], "Nombre no disponible")
                texto_linea = f"  • {celdas[0]} ➔ Gerencia: `{celdas[1]}` (*{nombre_persona}*) | Global: `{celdas[2]}`"
                
                if estado_ant and (info_linea not in estado_ant):
                    texto_linea = f"⚠️ {texto_linea}"
                    tipo_lista = "Ordinaria" if idx < 3 else "Discapacidad"
                    registrar_en_sheets(sheets_service, nombre, tipo_lista, celdas[0], celdas[1], celdas[2], fecha_sheets)
                elif not estado_ant:
                    tipo_lista = "Ordinaria" if idx < 3 else "Discapacidad"
                    registrar_en_sheets(sheets_service, nombre, tipo_lista, celdas[0], celdas[1], celdas[2], fecha_sheets)
                
                if idx < 3: 
                    lineas_ord.append(texto_linea)
                else: 
                    lineas_disc.append(texto_linea)

            with open(fichero_estado, "w") as f: 
                f.write(datos_actuales)
            print(f"💾 Archivo {fichero_estado} actualizado localmente.")
            
            txt_ord = "\n".join(lineas_ord)
            txt_disc = "\n".join(lineas_disc)
            
            msg = f"🔄 *SCS: {nombre}*\n📅 _Actualizado: {fecha_telegram}_\n🏥 *Fisioterapeuta*\n\n📋 *Ordinarios:*\n{txt_ord}\n\n👑 *Discapacidad:*\n{txt_disc}\n\n🔗 [Ver en la web]({URL_WEB})"
            enviar_telegram(msg, thread_id)
            
    except Exception as e:
        print(f"Error crítico procesando la gerencia {nombre}: {e}")

def main():
    sheets_service = obtener_servicio_sheets()
    for g in GERENCIAS_TOTALES:
        procesar_gerencia(sheets_service, g['nombre'], g['valor'], g['thread_id'])

if __name__ == "__main__":
    main()
