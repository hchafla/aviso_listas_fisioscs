import os
import re
import requests
import pdfplumber

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PDF_URL = "https://www3.gobiernodecanarias.org/sanidad/scs/content/cb750224-e0b8-11ec-9633-a3e478fed70d/Ultimos-llamamientos-LC-DrNegrin.pdf"
DB_FILE = "ultimo_negrin.txt"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")

def extraer_datos_negrin():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(PDF_URL, headers=headers)
    
    if response.status_code != 200:
        print(f"Error de conexión con el SCS (NEGRIN): {response.status_code}")
        return None

    with open("negrin.pdf", "wb") as f:
        f.write(response.content)

    texto_fila_fisioterapeuta = ""

    with pdfplumber.open("negrin.pdf") as pdf:
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
        print("No se localizó la fila de FISIOTERAPEUTA en el PDF de NEGRIN.")
        return None

    fechas = re.findall(r"\d{2}/\d{2}/\d{2,4}", texto_fila_fisioterapeuta)
    texto_sin_fechas = re.sub(r"\d{2}/\d{2}/\d{2,4}", "", texto_fila_fisioterapeuta)
    
    numeros = re.findall(r"\b\d+\b", texto_sin_fechas)
    numeros = [n for n in numeros if n != "2007"]

    if len(numeros) < 3 or len(fechas) < 3:
        print(f"Estructura NEGRIN inesperada. Números: {numeros}, Fechas: {fechas}")
        return None

    corta = f"{numeros[0]} ({fechas[0]})"
    larga = f"{numeros[1]} ({fechas[1]})"
    interinidad = f"{numeros[2]} ({fechas[2]})"

    return f"{corta}|{larga}|{interinidad}"

def controlar_cambios():
    datos_actuales = extraer_datos_negrin()
    if not datos_actuales:
        return

    datos_anteriores = ""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            datos_anteriores = f.read().strip()

    if datos_actuales != datos_anteriores:
        c_act, l_act, i_act = datos_actuales.split("|")
        
        try:
            c_ant, l_ant, i_ant = datos_anteriores.split("|")
        except:
            c_ant, l_ant, i_ant = "Ninguno", "Ninguno", "Ninguno"

        # Formateo con negrita condicional para las 3 categorías del Negrín
        l_c = f"• Corta Duración: {c_ant} ➔ {c_act}"
        if c_act != c_ant: l_c = f"• **Corta Duración: {c_ant} ➔ {c_act}**"

        l_l = f"• Larga Duración: {l_ant} ➔ {l_act}"
        if l_act != l_ant: l_l = f"• **Larga Duración: {l_ant} ➔ {l_act}**"

        l_i = f"• Interinidad: {i_ant} ➔ {i_act}"
        if i_act != i_ant: l_i = f"• **Interinidad: {i_ant} ➔ {i_act}**"

        mensaje = (
            "⚠️ **[ALERTA] Actualización Hospital NEGRÍN**\n"
            "Se han detectado cambios en los llamamientos de *Fisioterapeuta*:\n\n"
            f"{l_c}\n"
            f"{l_l}\n"
            f"{l_i}\n\n"
            f"🔗 [Abrir PDF Oficial]({PDF_URL})"
        )
        
        enviar_telegram(mensaje)

        with open(DB_FILE, "w") as f:
            f.write(datos_actuales)
    else:
        print("Sin cambios en el Hospital Negrín.")

if __name__ == "__main__":
    controlar_cambios()
