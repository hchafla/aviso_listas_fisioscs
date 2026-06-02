import os
import re
import requests
import pdfplumber

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# URL oficial del PDF de la GAPGC (Gran Canaria)
PDF_URL = "https://www3.gobiernodecanarias.org/sanidad/scs/content/f91bab10-92f7-11ec-9494-c360bb7ead96/Ultimos-llamamientos-LC-GranCanaria.pdf"
DB_FILE = "ultimo_gapgc.txt"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")

def extraer_datos_gapgc():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(PDF_URL, headers=headers)
    
    if response.status_code != 200:
        print(f"Error de conexión con el SCS (GAPGC): {response.status_code}")
        return None

    with open("gapgc.pdf", "wb") as f:
        f.write(response.content)

    texto_fila_fisioterapeuta = ""

    with pdfplumber.open("gapgc.pdf") as pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    if not fila:
                        continue
                    
                    celdas_limpias = [str(c).replace('\n', ' ').strip() for c in fila if c]
                    texto_completo = " ".join(celdas_limpias).upper()
                    
                    if "FISIOTERAPEUTA" in texto_completo:
                        texto_fila_fisioterapeuta = texto_completo
                        break
                if texto_fila_fisioterapeuta: break
            if texto_fila_fisioterapeuta: break

    if not texto_fila_fisioterapeuta:
        print("No se localizó la fila de FISIOTERAPEUTA en el PDF de GAPGC.")
        return None

    fechas = re.findall(r"\d{2}/\d{2}/\d{2,4}", texto_fila_fisioterapeuta)
    texto_sin_fechas = re.sub(r"\d{2}/\d{2}/\d{2,4}", "", texto_fila_fisioterapeuta)
    numeros = re.findall(r"\b\d+\b", texto_sin_fechas)
    numeros = [n for n in numeros if n != "2007"]

    if len(numeros) < 5 or len(fechas) < 5:
        print(f"Estructura GAPGC inesperada. Números: {numeros}, Fechas: {fechas}")
        return None

    ev_corta = f"{numeros[0]} ({fechas[0]})"
    ev_larga = f"{numeros[1]} ({fechas[1]})"
    sust_corta = f"{numeros[2]} ({fechas[2]})"
    sust_larga = f"{numeros[3]} ({fechas[3]})"
    interinidad = f"{numeros[4]} ({fechas[4]})"

    return f"{ev_corta}|{ev_larga}|{sust_corta}|{sust_larga}|{interinidad}"

def controlar_cambios():
    datos_actuales = extraer_datos_gapgc()
    if not datos_actuales:
        return

    datos_anteriores = ""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            datos_anteriores = f.read().strip()

    if datos_actuales != datos_anteriores:
        ec_act, el_act, sc_act, sl_act, in_act = datos_actuales.split("|")
        
        try:
            ec_ant, el_ant, sc_ant, sl_ant, in_ant = datos_anteriores.split("|")
        except:
            ec_ant, el_ant, sc_ant, sl_ant, in_ant = "Ninguno", "Ninguno", "Ninguno", "Ninguno", "Ninguno"

        mensaje = (
            "⚠️ **[ALERTA] Actualización GAP Gran Canaria**\n"
            "Cambios detectados en *Fisioterapeuta*:\n\n"
            f"• **Ev. Corta Duración:**\n  Antes: {ec_ant}\n  Ahora: **{ec_act}**\n\n"
            f"• **Ev. Larga Duración:**\n  Antes: {el_ant}\n  Ahora: **{el_act}**\n\n"
            f"• **Sust. Corta Duración:**\n  Antes: {sc_ant}\n  Ahora: **{sc_act}**\n\n"
            f"• **Sust. Larga Duración:**\n  Antes: {sl_ant}\n  Ahora: **{sl_act}**\n\n"
            f"• **Interinidad:**\n  Antes: {in_ant}\n  Ahora: **{in_act}**\n\n"
            f"🔗 [Abrir PDF Oficial]({PDF_URL})"
        )
        
        enviar_telegram(mensaje)

        with open(DB_FILE, "w") as f:
            f.write(datos_actuales)
    else:
        print("Sin cambios en la GAPGC.")

if __name__ == "__main__":
    controlar_cambios()
