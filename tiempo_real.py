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
            print("Error: El servidor rechazó la primera fase.")
            return

        # Paso 3: Enviar Categoría Fisioterapeuta (Valor 97)
        print("Paso 3: Enviando selección de Categoría (FISIOTERAPEUTA)...")
        payload_categoria = {
            "j_idt13": "j_idt13",
            "j_idt13:categoriasSOM_input": "97",
            "j_idt13:categoriasSOM_focus": "",
            "j_idt13:j_idt16": "Seleccionar",
            "javax.faces.ViewState": vs_2
        }
        
        r_final = session.post(url_cat, data=payload_categoria, timeout=15)
        
        # Paso 4: Procesar resultados mediante búsqueda semántica elemental
        print("Paso 4: Analizando datos mediante árbol de elementos...")
        soup_final = BeautifulSoup(r_final.text, "html.parser")
        
        lineas_ordinario = []
        lineas_discapacidad = []
        datos_control = ""

        # Buscamos todas las tablas del documento
        tablas = soup_final.find_all("table")
        
        for tabla in tablas:
            # Identificamos el contexto de la tabla buscando texto en sus sub-cabeceras o elementos previos
            texto_tabla = tabla.get_text()
            
            es_discapacidad = "discapacidad" in texto_tabla.lower() or "cupo" in texto_tabla.lower()
            
            filas = tabla.find_all("tr")
            for fila in filas:
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                if len(celdas) >= 3:
                    tipo = celdas[0]
                    if any(kw in tipo for kw in ["Corta duración", "Larga duración", "Interinidad"]):
                        pos_gerencia = celdas[1] if celdas[1] else "-"
                        pos_global = celdas[2] if celdas[2] else "-"
                        
                        linea = f"  • {tipo} ➔ Gerencia: `{pos_gerencia}` | Global: `{pos_global}`"
                        token_control = f"{tipo}:{pos_gerencia}-{pos_global}"
                        
                        # Clasificación unívoca basada en la presencia de metadatos de discapacidad
                        if es_discapacidad:
                            if linea not in lineas_discapacidad:
                                lineas_discapacidad.append(linea)
                                datos_control += f"DISC_{token_control}|"
                        else:
                            if linea not in lineas_ordinario:
                                lineas_ordinario.append(linea)
                                datos_control += f"ORD_{token_control}|"

        # Construcción del cuerpo del mensaje si existen datos reales
        if not datos_control:
            print("Error: No se ha podido extraer ningún dato numérico válido.")
            return

        lineas_mensaje = []
        if lineas_ordinario:
            lineas_mensaje.append("📋 *Nombramientos Ordinarios:*")
            lineas_mensaje.extend(lineas_ordinario)
            lineas_mensaje.append("")
            
        if lineas_discapacidad:
            lineas_mensaje.append("♿ *Cupo Personas con Discapacidad:*")
            lineas_mensaje.extend(lineas_discapacidad)
            lineas_mensaje.append("")

        # Control de persistencia
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
            print("¡Éxito! Estructura corregida y enviada a Telegram.")
        else:
            print("Sin novedades. Los datos coinciden con el registro de control.")

    except Exception as e:
        print(f"Fallo en la extracción por conexiones directas: {e}")

if __name__ == "__main__":
    consultar_llamamientos_directo()
