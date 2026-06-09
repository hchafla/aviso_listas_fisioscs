import os
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FICHERO_ESTADO = "ultimo_estado_fisio.txt"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def consultar_scs():
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    url_action = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        # 1. Petición inicial para establecer cookies y pescar el ViewState obligatorio
        r_inicio = session.get(url_base, timeout=15)
        soup_inicio = BeautifulSoup(r_inicio.text, "html.parser")
        
        view_state_input = soup_inicio.find("input", {"name": "javax.faces.ViewState"})
        if not view_state_input:
            print("Error: No se pudo localizar el ViewState de JSF.")
            return
        view_state = view_state_input["value"]

        # 2. Payload exacto emulando los códigos internos del SCS (Negrín + Fisioterapeuta)
        # Nota: Usamos las estructuras estándar detectadas en los formularios JSF del SCS
        payload = {
            "formulario": "formulario",
            "formulario:gerencia": "11",      # ID del Hospital Dr. Negrín
            "formulario:categoria": "55",     # ID de Fisioterapeuta
            "formulario:btnBuscar": "Buscar",
            "javax.faces.ViewState": view_state
        }

        # 3. Ejecutar el POST simulando el clic humano
        r_resultado = session.post(url_action, data=payload, timeout=15)
        soup_resultado = BeautifulSoup(r_resultado.text, "html.parser")

        # 4. Localizar la tabla de resultados en el HTML devuelto
        tabla = soup_resultado.find("table")
        if not tabla:
            print("La tabla de llamamientos no apareció en el HTML. Comprobar IDs del SCS.")
            return

        # 5. Extraer y procesar los datos de las celdas
        lineas = []
        datos_control = ""
        for fila in tabla.find_all("tr")[1:]:
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            if len(celdas) >= 3:
                tipo, pos_gerencia, pos_global = celdas[0], celdas[1], celdas[2]
                lineas.append(f"📌 *{tipo}*\n   ↳ Gerencia: `{pos_gerencia}` | Global: `{pos_global}`")
                datos_control += f"{tipo}:{pos_gerencia}-{pos_global}|"

        if not lineas:
            print("Tabla localizada pero vacía de contenido.")
            return

        # 6. Control de cambios para evitar spam repetitivo
        estado_anterior = ""
        if os.path.exists(FICHERO_ESTADO):
            with open(FICHERO_ESTADO, "r", encoding="utf-8") as f:
                estado_anterior = f.read().strip()

        if datos_control != estado_anterior:
            # Guardamos el nuevo estado inmediatamente
            with open(FICHERO_ESTADO, "w", encoding="utf-8") as f:
                f.write(datos_control)
                
            # Construimos el mensaje estético para Telegram
            mensaje = "🔄 *SCS TIEMPO REAL: CAMBIO DETECTADO*\n"
            mensaje += "🏥 _Hospital Dr. Negrín — Fisioterapeutas_\n\n"
            mensaje += "\n".join(lineas)
            mensaje += f"\n\n🔗 [Acceso al Portal del SCS]({url_base})"
            
            enviar_telegram(mensaje)
            print("Cambio detectado. Mensaje enviado a Telegram.")
        else:
            print("Sin cambios en los llamamientos con respecto a la última revisión.")

    except Exception as e:
        print(f"Error crítico en la ejecución: {e}")

if __name__ == "__main__":
    consultar_scs()
