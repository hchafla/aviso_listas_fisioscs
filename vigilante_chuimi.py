import os
import re
import requests
import pdfplumber

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PDF_URL = "https://www3.gobiernodecanarias.org/sanidad/scs/content/8c3af03c-f2c3-11ec-9bc5-97e32709ae66/Ultimos-llamamientos-LC-CHUIMI.pdf"
DB_FILE = "ultimo_chuimi.txt"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")

def extraer_datos_chuimi():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(PDF_URL, headers=headers)
    
    if response.status_code != 200:
        print(f"Error de conexión con el SCS: {response.status_code}")
        return None

    with open("chuimi.pdf", "wb") as f:
        f.write(response.content)

    encontrado_fisioterapeuta = False
    texto_fila_general = ""

    with pdfplumber.open("chuimi.pdf") as pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    if not fila:
                        continue
                    
                    celdas_limpias = [str(c).replace('\n', ' ').strip() for c in fila if c]
                    texto_completo = " ".join(celdas_limpias).upper()
                    
                    if "FISIOTERAPEUTA" in texto_completo:
                        encontrado_fisioterapeuta = True
                    
                    if encontrado_fisioterapeuta and "GENERAL" in texto_completo:
                        texto_fila_general = texto_completo
                        break
                if texto_fila_general: break
            if texto_fila_general: break

    if not texto_fila_general:
        print("No se localizó la fila de Fisioterapeuta General.")
        return None

    texto_procesar = texto_fila_general.replace("GENERAL", "")
    
    fechas = re.findall(r"\d{2}/\d{2}/\d{4}", texto_procesar)
    numeros = re.findall(r"\b\d+\b", re.sub(r"\d{2}/\d{2}/\d{4}", "", texto_procesar))
    numeros = [n for n in numeros if n != "2007"]

    if len(numeros) < 3 or len(fechas) < 3:
        print(f"Estructura de datos incompleta. Números: {numeros}, Fechas: {fechas}")
        return None

    corta = f"{numeros[0]} ({fechas[0]})"
    larga = f"{numeros[1]} ({fechas[1]})"
    interinidad = f"{numeros[2]} ({fechas[2]})"

    return f"{corta}|{larga}|{interinidad}"

def controlar_cambios():
    datos_actuales = extraer_datos_chuimi()
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

        # Evaluamos individualmente qué ha cambiado para aplicar la negrita selectiva
        linea_corta = f"• Corta Duración: {c_ant} ➔ {c_act}"
        if c_act != c_ant:
            linea_corta = f"• **Corta Duración: {c_ant} ➔ {c_act}**"

        linea_larga = f"• Larga Duración: {l_ant} ➔ {l_act}"
        if l_act != l_ant:
            linea_larga = f"• **Larga Duración: {l_ant} ➔ {l_act}**"

        linea_interinidad = f"• Interinidad: {i_ant} ➔ {i_act}"
        if i_act != i_ant:
            linea_interinidad = f"• **Interinidad: {i_ant} ➔ {i_act}**"

        # He compactado el formato visual para que ocupe menos espacio en tu pantalla y sea más directo
        mensaje = (
            "⚠️ **[ALERTA] Actualización CHUIMI**\n"
            "Cambios detectados en *Fisioterapeuta (General)*:\n\n"
            f"{linea_corta}\n"
            f"{linea_larga}\n"
            f"{linea_interinidad}\n\n"
            f"🔗 [Abrir PDF Oficial]({PDF_URL})"
        )
        
        enviar_telegram(mensaje)

        with open(DB_FILE, "w") as f:
            f.write(datos_actuales)
    else:
        print("El documento se mantiene sin cambios para Fisioterapeuta General.")

if __name__ == "__main__":
    controlar_cambios()
