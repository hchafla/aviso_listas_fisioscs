import os
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
    fila_general_limpia = None

    with pdfplumber.open("chuimi.pdf") as pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    if not fila:
                        continue
                    
                    # Convertimos la fila a una lista de textos limpios (quitando "None" y saltos de línea)
                    celdas_limpias = [str(c).replace('\n', ' ').strip() for c in fila if c]
                    texto_completo = " ".join(celdas_limpias).upper()
                    
                    if "FISIOTERAPEUTA" in texto_completo:
                        encontrado_fisioterapeuta = True
                    
                    # Si ya pasamos por Fisioterapeuta y esta fila contiene los datos de 'GENERAL'
                    if encontrado_fisioterapeuta and "GENERAL" in texto_completo:
                        # Al estar descuadrada por la celda combinada de Fisioterapeuta, 
                        # eliminamos la palabra 'GENERAL' si aparece para normalizar los datos numéricos.
                        fila_general_limpia = [c for c in celdas_limpias if c.upper() != "GENERAL"]
                        break
                if fila_general_limpia: break
            if fila_general_limpia: break

    if not fila_general_limpia or len(fila_general_limpia) < 6:
        print("No se pudo estructurar correctamente la fila de Fisioterapeuta General.")
        return None

    # Tras limpiar la celda combinada, el orden estricto de los datos en el PDF del CHUIMI es:
    # [0] Nº Orden Corta, [1] Fecha Corta, [2] Nº Orden Larga, [3] Fecha Larga, [4] Nº Orden Interinidad, [5] Fecha Interinidad
    corta_no = fila_general_limpia[0]
    corta_fec = fila_general_limpia[1]
    larga_no = fila_general_limpia[2]
    larga_fec = fila_general_limpia[3]
    interinidad_no = fila_general_limpia[4]
    interinidad_fec = fila_general_limpia[5]

    # Guardamos el bloque estructurado completo para detectar cualquier cambio en números o fechas
    return f"{corta_no} ({corta_fec})|{larga_no} ({larga_fec})|{interinidad_no} ({interinidad_fec})"

def controlar_cambios():
    datos_actuales = extraer_datos_chuimi()
    if not datos_actuales:
        return

    datos_anteriores = ""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            datos_anteriores = f.read().strip()

    if datos_actuales != datos_anteriores:
        # Desempaquetamos los datos actuales
        c_act, l_act, i_act = datos_actuales.split("|")
        
        # Desempaquetamos los datos anteriores si existen para la comparativa
        try:
            c_ant, l_ant, i_ant = datos_anteriores.split("|")
        except:
            c_ant, l_ant, i_ant = "Ninguno", "Ninguno", "Ninguno"

        mensaje = (
            "⚠️ **[ALERTA] Actualización CHUIMI**\n"
            "Se han detectado cambios en los llamamientos de *Fisioterapeuta (General)*:\n\n"
            f"• **Corta Duración:**\n  Antes: {c_ant}\n  Ahora: **{c_act}**\n\n"
            f"• **Larga Duración:**\n  Antes: {l_ant}\n  Ahora: **{l_act}**\n\n"
            f"• **Interinidad:**\n  Antes: {i_ant}\n  Ahora: **{i_act}**\n\n"
            f"🔗 [Abrir PDF Oficial]({PDF_URL})"
        )
        
        enviar_telegram(mensaje)

        with open(DB_FILE, "w") as f:
            f.write(datos_actuales)
    else:
        print("El documento se mantiene sin cambios para Fisioterapeuta General.")

if __name__ == "__main__":
    controlar_cambios()
