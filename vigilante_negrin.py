import os
import re
import requests
import pdfplumber

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# URL oficial del PDF del Hospital Doctor Negrín
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

    texto_linea_fisioterapeuta = ""

    with pdfplumber.open("negrin.pdf") as pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    if not fila:
                        continue
                    
                    # Unificamos el texto de las celdas de la fila
                    celdas_limpias = [str(c).replace('\n', ' ').strip() for c in fila if c]
                    texto_completo = " ".join(celdas_limpias).upper()
                    
                    # Buscamos la fila específica de Fisioterapeuta
                    # Validamos que contenga "FISIOTERAPEUTA" pero evitamos que se confunda si existieran perfiles especiales de otra cosa
                    if "FISIOTERAPEUTA" in texto_completo:
                        texto_linea_fisioterapeuta = texto_completo
                        break
                if texto_linea_fisioterapeuta: break
            if texto_linea_fisioterapeuta: break

    if not texto_linea_fisioterapeuta:
        print("No se localizó la fila de FISIOTERAPEUTA en el PDF de NEGRIN.")
        return None

    # Extraemos la fecha (DD/MM/AAAA)
    fechas = re.findall(r"\d{2}/\d{2}/\d{4}", texto_linea_fisioterapeuta)
    
    # Extraemos el número de orden limpiando la fecha para que sus dígitos no interfieran
    texto_sin_fechas = re.sub(r"\d{2}/\d{2}/\d{4}", "", texto_linea_fisioterapeuta)
    numeros = re.findall(r"\b\d+\b", texto_sin_fechas)
    numeros = [n for n in numeros if n != "2007"] # Filtro de seguridad por la OPE

    if not numeros or not fechas:
        print(f"Estructura NEGRIN inesperada. Texto obtenido: {texto_linea_fisioterapeuta}")
        return None

    # En este formato, el primer número es el orden de corte y la primera fecha es su actualización
    return f"{numeros[0]} ({fechas[0]})"

def controlar_cambios():
    datos_actuales = extraer_datos_negrin()
    if not datos_actuales:
        return

    datos_anteriores = ""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            datos_anteriores = f.read().strip()

    if datos_actuales != datos_anteriores:
        mensaje = (
            "⚠️ **[ALERTA] Actualización Hospital NEGRÍN**\n"
            "Se han detectado cambios en el último llamamiento de *Fisioterapeuta*:\n\n"
            f"• **Último Llamamiento:**\n"
            f"  Antes: {datos_anteriores or 'Ninguno'}\n"
            f"  Ahora: **{datos_actuales}**\n\n"
            f"🔗 [Abrir PDF Oficial]({PDF_URL})"
        )
        
        enviar_telegram(mensaje)

        with open(DB_FILE, "w") as f:
            f.write(datos_actuales)
    else:
        print("Sin cambios en el Hospital Negrín.")

if __name__ == "__main__":
    controlar_cambios()
