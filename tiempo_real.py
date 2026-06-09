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
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    url_cat = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Connection": "keep-alive"
    })

    try:
        # Paso 1: Conectar a la Home y extraer ViewState inicial
        print("Paso 1: Obteniendo ViewState inicial...")
        r_home = session.get(url_base, timeout=15)
        vs_1 = extraer_view_state(r_home.text)
        
        if not vs_1:
            print("Error: No se pudo obtener el ViewState inicial.")
            return

        # Paso 2: Enviar Hospital Negrín (Valor 21)
        print("Paso 2: Enviando selección de Gerencia (Hospital Negrín)...")
        payload_gerencia = {
            "j_idt43": "j_idt43",
            "j_idt43:gerenciaUNSOM_input": "21",
            "j_idt43:gerenciaUNSOM_focus": "",
            "j_idt43:j_idt46": "Seleccionar",
            "javax.faces.ViewState": vs_1
        }
        
        r_categorias = session.post(url_base, data=payload_gerencia, timeout=15)
        vs_2 = extraer_view_state(r_categorias.text)
        
        if not vs_2:
            print("Error: El servidor rechazó la primera fase (ViewState 2 no recibido).")
            return

        # Paso 3: Enviar Categoría Fisioterapeuta (Valor 97) a la URL correcta
        print("Paso 3: Enviando selección de Categoría (FISIOTERAPEUTA)...")
        payload_categoria = {
            "j_idt13": "j_idt13",
            "j_idt13:categoriasSOM_input": "97",
            "j_idt13:categoriasSOM_focus": "",
            "j_idt13:j_idt16": "Seleccionar",
            "javax.faces.ViewState": vs_2
        }
        
        r_final = session.post(url_cat, data=payload_categoria, timeout=15)
        
        # Paso 4: Procesar la tabla de resultados finales
        print("Paso 4: Analizando tabla final de resultados...")
        soup_final = BeautifulSoup(r_final.text, "html.parser")
        tablas = soup_final.find_all("table")
        
        if not tablas:
            print("Error: No se encontraron tablas en la respuesta final.")
            return

        lineas_mensaje = []
        datos_control = ""
        titulos_tablas = ["📋 *Nombramientos Ordinarios:*", "♿ *Cupo Personas con Discapacidad:*"]

        for i, tabla in enumerate(tablas):
            if i >= len(titulos_tablas):
                break
            
            filas_datos = [fila for fila in tabla.find_all("tr") if fila.find("td")]

            if filas_datos:
                lineas_mensaje.append(titulos_tablas[i])
                for fila in filas_datos:
                    celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                    if len(celdas) >= 3:
                        tipo, pos_gerencia, pos_global = celdas[0], celdas[1], celdas[2]
                        pos_gerencia = pos_gerencia if pos_gerencia else "-"
                        pos_global = pos_global if pos_global else "-"
                        lineas_mensaje.append(f"  • {tipo} ➔ Gerencia: `{pos_gerencia}` | Global: `{pos_global}`")
                        datos_control += f"{tipo}:{pos_gerencia}-{pos_global}|"
                lineas_mensaje.append("")

        if not datos_control:
            print("Estructura correcta pero las tablas no contienen filas numéricas.")
            return

        # Control de Persistencia y Alerta en Telegram
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
            mensaje_final += f"\n🔗 [Verificar Web]({url_base})"
            
            enviar_telegram(mensaje_final)
            print("¡Éxito! Datos extraídos y notificación enviada.")
        else:
            print("Sin novedades. Los datos coinciden con el último registro.")

    except Exception as e:
        print(f"Fallo en la conexión directa: {e}")

if __name__ == "__main__":
    consultar_llamamientos_directo()
