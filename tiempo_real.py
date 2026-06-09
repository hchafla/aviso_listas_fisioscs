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

def extraer_view_state(html):
    soup = BeautifulSoup(html, "html.parser")
    input_vs = soup.find("input", {"name": "javax.faces.ViewState"})
    if input_vs:
        return input_vs.get("value")
    return None

def consultar_llamamientos_directo():
    url = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Connection": "keep-alive"
    })

    try:
        # Petición 1: Obtener la Home y el ViewState inicial
        print("Paso 1: Conectando a la Home...")
        r_home = session.get(url, timeout=15)
        vs_1 = extraer_view_state(r_home.text)
        
        if not vs_1:
            print("Error: No se pudo obtener el ViewState inicial.")
            return

        # Petición 2: Simular el envío de la Gerencia (Bloque 3)
        # Usamos los IDs exactos de PrimeFaces que aparecían en tus capturas de pantalla (j_idt43)
        print("Paso 2: Enviando selección de Gerencia (Hospital Negrín)...")
        payload_gerencia = {
            "j_idt43": "j_idt43",
            "j_idt43:gerenciaUNSOM_input": "Hospital Universitario de Gran Canaria Doctor Negrín",
            "j_idt43:gerenciaUNSOM_focus": "",
            "j_idt43:btnSeleccionarGerenciaUNSOM": "Seleccionar",
            "javax.faces.ViewState": vs_1
        }
        
        r_categorias = session.post(url, data=payload_gerencia, timeout=15)
        vs_2 = extraer_view_state(r_categorias.text)
        
        if not vs_2:
            print("Error: El servidor rechazó la selección de Gerencia (ViewState 2 no recibido).")
            return

        # Petición 3: Simular el envío de la Categoría (FISIOTERAPEUTA) en la página mutada
        print("Paso 3: Enviando selección de Categoría (FISIOTERAPEUTA)...")
        payload_categoria = {
            "formulario": "formulario",
            "formulario:categoriaUNSOM_input": "FISIOTERAPEUTA",
            "formulario:categoriaUNSOM_focus": "",
            "formulario:btnBuscarLlamamientos": "Seleccionar",
            "javax.faces.ViewState": vs_2
        }
        
        # Al procesar el segundo formulario, el backend redirige internamente usando los mismos datos de sesión
        r_final = session.post(url, data=payload_categoria, timeout=15)
        
        # Procesamiento final del HTML
        print("Paso 4: Procesando tablas de resultados...")
        soup_final = BeautifulSoup(r_final.text, "html.parser")
        tablas = soup_final.find_all("table")
        
        if not tablas:
            print("Error: No se encontraron tablas. Es probable que los nombres de los inputs hayan cambiado.")
            # Si falla, imprimimos una muestra para ver qué IDs nuevos ha generado el servidor
            print(f"Muestra del HTML final recibido (primeros 600 bytes): {r_final.text[:600]}")
            return

        lineas_mensaje = []
        datos_control = ""
        titulos_tablas = ["📋 *Nombramientos Ordinarios:*", "♿ *Cupo Personas con Discapacidad:*"]

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
            print("Tablas localizadas pero vacías.")
            return

        # Control de Persistencia y Alertas
        estado_anterior = ""
        if os.path.exists(FICHERO_ESTADO):
            with open(FICHERO_ESTADO, "r", encoding="utf-8") as f:
                estado_anterior = f.read().strip()

        if datos_control != estado_anterior:
            with open(FICHERO_ESTADO, "w", encoding="utf-8") as f:
                f.write(datos_control)
                
            mensaje_final = "🔄 *SCS TIEMPO REAL: LLAMAMIENTOS*\n"
            mensaje_final += "🏥 _Hospital Dr. Negrín — FISIOTERAPEUTA_\n\n"
            mensaje_final += "\n".join(lineas_mensaje)
            mensaje_final += f"\n🔗 [Verificar Web]({url})"
            
            enviar_telegram(mensaje_final)
            print("¡Éxito! Mensaje enviado a Telegram.")
        else:
            print("Sin novedades. Los datos coinciden.")

    except Exception as e:
        print(f"Fallo en la conexión directa: {e}")

if __name__ == "__main__":
    consultar_llamamientos_directo()
