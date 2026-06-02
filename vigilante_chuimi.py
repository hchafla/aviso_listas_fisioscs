import os
import requests
import pdfplumber

# Configuración de entorno (Se gestiona en GitHub Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# URL oficial del PDF del CHUIMI
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

    corta, larga, interinidad = "---", "---", "---"
    encontrado_fisioterapeuta = False

    # Utilizaremos pdfplumber para inspeccionar las tablas del PDF
    with pdfplumber.open("chuimi.pdf") as pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables()
            for tabla in tablas:
                for i, fila in enumerate(tabla):
                    # Filtramos filas vacías o corruptas
                    if not fila or len(fila) < 4:
                        continue
                    
                    # Buscamos la fila donde aparece la palabra clave
                    texto_fila = "".join([str(celda) for celda in fila if celda]).upper()
                    
                    if "FISIOTERAPEUTA" in texto_fila:
                        encontrado_fisioterapeuta = True
                        
                    # Si ya encontramos la sección, buscamos la subfila 'GENERAL'
                    if encontrado_fisioterapeuta and "GENERAL" in texto_fila:
                        # Dependiendo de cómo pdfplumber estructure las columnas de esta tabla:
                        # Limpiamos los saltos de línea internos que suelen meter las celdas del SCS
                        valores = [str(celda).replace('\n', ' ').strip() for celda in fila if celda]
                        
                        # Mapeo posicional según la estructura visual de la Imagen 3:
                        # [0] GENERAL, [1] Nº Corta, [2] Fecha Corta, [3] Nº Larga...
                        try:
                            # Buscamos los números de orden limpiando letras (ej: '389-S' -> '389')
                            corta = valores[1].split()[0] if len(valores) > 1 else "---"
                            larga = valores[3].split()[0] if len(valores) > 3 else "---"
                            interinidad = valores[5].split()[0] if len(valores) > 5 else "---"
                        except Exception as e:
                            print(f"Error al indexar las columnas de la tabla: {e}")
                        break
                if corta != "---": break
            if corta != "---": break

    if corta == "---" and larga == "---":
        print("No se pudo parsear correctamente la fila de Fisioterapeuta General.")
        return None

    return f"CORTA:{corta}|LARGA:{larga}|INTERINIDAD:{interinidad}"

def controlar_cambios():
    datos_actuales = extraer_datos_chuimi()
    if not datos_actuales:
        return

    # Leer el estado anterior
    datos_anteriores = ""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            datos_anteriores = f.read().strip()

    # Si hay cambios, enviamos el desglose limpio a Telegram
    if datos_actuales != datos_anteriores:
        c_act, l_act, i_act = [d.split(":")[1] for d in datos_actuales.split("|")]
        
        # Intentamos desempaquetar el anterior si existía para mostrar la comparativa
        try:
            c_ant, l_ant, i_ant = [d.split(":")[1] for d in datos_anteriores.split("|")]
        except:
            c_ant, l_ant, i_ant = "🔍", "🔍", "🔍"

        mensaje = (
            "⚠️ **[ALERTA] Actualización CHUIMI**\n"
            "Se han detectado cambios en los llamamientos de *Fisioterapeuta (General)*:\n\n"
            f"• **Corta Duración:** {c_ant} ➔ **{c_act}**\n"
            f"• **Larga Duración:** {l_ant} ➔ **{l_act}**\n"
            f"• **Interinidad:** {i_ant} ➔ **{i_act}**\n\n"
            f"🔗 [Abrir PDF Oficial]({PDF_URL})"
        )
        
        enviar_telegram(mensaje)

        # Guardamos el nuevo estado para la siguiente ejecución
        with open(DB_FILE, "w") as f:
            f.write(datos_actuales)
    else:
        print("El documento se mantiene sin cambios para Fisioterapeuta General.")

if __name__ == "__main__":
    controlar_cambios()
