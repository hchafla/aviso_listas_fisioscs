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
    url_home = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    url_portal = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9"
    })

    try:
        # Step 1: Entrar a la HOME para inicializar la cookie de sesión (JSESSIONID)
        print("Estableciendo sesión inicial en la Home...")
        session.get(url_home, timeout=15)
        
        # Step 2: Cargar la página de categorías usando la sesión ya abierta
        print("Cargando el formulario de llamamientos...")
        r_portal = session.get(url_portal, timeout=15)
        soup_inicio = BeautifulSoup(r_portal.text, "html.parser")
        
        view_state_input = soup_inicio.find("input", {"name": "javax.faces.ViewState"})
        if not view_state_input:
            print("Error persistente: No se localiza el ViewState.")
            # Si vuelve a fallar, imprimimos los primeros 500 caracteres para ver qué responde el SCS
            print(f"Muestra del HTML recibido:\n{r_portal.text[:500]}")
            return
            
        view_state = view_state_input["value"]
        print(f"ViewState localizado con éxito: {view_state[:20]}...")

        # Step 3: Construcción del Payload con los parámetros UNSOM
        payload = {
            "formulario": "formulario",
            "formulario:gerenciaUNSOM_input": "Hospital Universitario de Gran Canaria Doctor Negrín",
            "formulario:gerenciaUNSOM_focus": "",
            "formulario:categoriaUNSOM_input": "FISIOTERAPEUTA",
            "formulario:categoriaUNSOM_focus": "",
            "formulario:btnBuscarLlamamientos": "Buscar",
            "javax.faces.ViewState": view_state
        }

        # Step 4: Envío de la consulta
        print("Enviando parámetros de búsqueda...")
        r_resultado = session.post(url_portal, data=payload, timeout=15)
        soup_resultado = BeautifulSoup(r_resultado.text, "html.parser")

        # Step 5: Procesamiento de tablas
        tablas = soup_resultado.find_all("table")
        if not tablas:
            print("No se encontraron tablas en el HTML de respuesta.")
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
            print("Tablas localizadas pero sin celdas de datos legibles.")
            return

        # Step 6: Control de cambios
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
            mensaje_final += f"🔗 [Verificar en la Web Oficial del SCS]({url_portal})"
            
            enviar_telegram(mensaje_final)
            print("Datos procesados correctamente. Mensaje enviado a Telegram.")
        else:
            print("Los datos coinciden con el registro previo. Sin cambios.")

    except Exception as e:
        print(f"Error crítico en la ejecución: {e}")

if __name__ == "__main__":
    consultar_llamamientos_scs()
