import os
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FICHERO_ESTADO = "ultimo_estado_llamamientos.txt"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def consultar_llamamientos_scs():
    url_portal = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    
    session = requests.Session()
    # Cabeceras de simulación completa para evitar que PrimeFaces corte la conexión
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": "1"
    })

    try:
        # Petición directa a la sección de categorías simulando una navegación orgánica limpia
        print("Solicitando formulario de llamamientos...")
        r_portal = session.get(url_portal, timeout=20)
        
        soup_inicio = BeautifulSoup(r_portal.text, "html.parser")
        
        # Intentamos localizar el ViewState buscando variaciones del componente JSF
        view_state_input = soup_inicio.find("input", {"name": "javax.faces.ViewState"})
        
        if not view_state_input:
            # Intento de rescate alternativo si el ID está formateado de forma distinta
            view_state_input = soup_inicio.find(id=lambda x: x and "ViewState" in x)

        if not view_state_input:
            print("Error: El servidor del SCS bloqueó el formulario completo.")
            print(f"Longitud del HTML devuelto: {len(r_portal.text)} bytes (Si es menor de 5000, está capado)")
            return
            
        view_state = view_state_input.get("value")
        print(f"ViewState capturado con éxito de forma limpia.")

        # Payload definitivo mapeado con las variables UNSOM (Últimos Nombramientos)
        payload = {
            "formulario": "formulario",
            "formulario:gerenciaUNSOM_input": "Hospital Universitario de Gran Canaria Doctor Negrín",
            "formulario:gerenciaUNSOM_focus": "",
            "formulario:categoriaUNSOM_input": "FISIOTERAPEUTA",
            "formulario:categoriaUNSOM_focus": "",
            "formulario:btnBuscarLlamamientos": "Buscar",
            "javax.faces.ViewState": view_state
        }

        print("Enviando petición de extracción de datos...")
        r_resultado = session.post(url_portal, data=payload, timeout=20)
        soup_resultado = BeautifulSoup(r_resultado.text, "html.parser")

        tablas = soup_resultado.find_all("table")
        if not tablas:
            print("No se encontraron tablas de datos. El servidor rechazó los parámetros del formulario.")
            return

        lineas_mensaje = []
        datos_control = ""
        titulos_tablas = [
            "📋 *Nombramientos Ordinarios:*",
            "♿ *Cupo Personas con Discapacidad:*"
        ]

        for i, tabla in enumerate(tablas):
            if i >= len(titulos_tablas):
                break
                
            filas = tabla.find_all("tr")[1:]
            if filas:
                lineas_mensaje.append(titulos_tablas[i])
                
            for fila in filas:
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                if len(celdas) >= 3:
                    tipo, pos_gerencia, pos_global = celdas[0], celdas[1], celdas[2]
                    pos_gerencia = pos_gerencia if pos_gerencia else "-"
                    pos_global = pos_global if pos_global else "-"
                    
                    lineas_mensaje.append(f"  • {tipo} ➔ Gerencia: `{pos_gerencia}` | Global: `{pos_global}`")
                    datos_control += f"{tipo}:{pos_gerencia}-{pos_global}|"
            lineas_mensaje.append("")

        if not datos_control:
            print("Estructura de tabla localizada pero sin datos legibles.")
            return

        # Lógica de verificación contra el estado guardado
        estado_anterior = ""
        if os.path.exists(FICHERO_ESTADO):
            with open(FICHERO_ESTADO, "r", encoding="utf-8") as f:
                estado_anterior = f.read().strip()

        if datos_control != estado_anterior:
            with open(FICHERO_ESTADO, "w", encoding="utf-8") as f:
                f.write(datos_control)
                
            mensaje_final = "🔄 *SCS TIEMPO REAL: ACTUALIZACIÓN DE LLAMAMIENTOS*\n"
            mensaje_final += "🏥 _Hospital Dr. Negrín — FISIOTERAPEUTA_\n\n"
            mensaje_final += "\n".join(lineas_mensaje)
            mensaje_final += f"🔗 [Verificar en la Web Oficial]({url_portal})"
            
            enviar_telegram(mensaje_final)
            print("Proceso finalizado. Mensaje enviado a Telegram.")
        else:
            print("Sin novedades en las listas.")

    except Exception as e:
        print(f"Fallo durante la ejecución del script: {e}")

if __name__ == "__main__":
    consultar_llamamientos_scs()
