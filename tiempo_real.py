import os
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import requests

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

async def consultar_llamamientos():
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    
    async with async_playwright() as p:
        print("Iniciando navegador virtual...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES"
        )
        page = await context.new_page()
        
        print(f"Conectando a la Home: {url_base}")
        await page.goto(url_base, wait_until="networkidle")
        
        # 1. PASO: SELECCIÓN DE GERENCIA (BLOQUE 3)
        print("Abriendo el menú de Gerencia (Bloque 3)...")
        # Apuntamos al elemento que contiene el identificador único visible en el inspector
        await page.click("div[id*='gerenciaUNSOM']")
        await page.wait_for_timeout(1000)
        
        print("Seleccionando 'Hospital Universitario de Gran Canaria Doctor Negrín'...")
        # Forzamos el click en la opción de la lista correspondiente a su ID de panel
        await page.click("div[id*='gerenciaUNSOM_panel'] li[data-label='Hospital Universitario de Gran Canaria Doctor Negrín']")
        await page.wait_for_timeout(1000)
        
        print("Pulsando el botón 'Seleccionar' de Gerencia...")
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            # Hacemos click en el botón específico de este bloque
            await page.click("button[id*='btnSeleccionarGerenciaUNSOM']")
        
        print("Página de categorías cargada con éxito.")
        await page.wait_for_timeout(1500)

        # 2. PASO: SELECCIÓN DE CATEGORÍA
        print("Abriendo el menú de Categorías...")
        await page.click("div[id*='categoriaUNSOM']")
        await page.wait_for_timeout(1000)
        
        print("Seleccionando 'FISIOTERAPEUTA'...")
        await page.click("div[id*='categoriaUNSOM_panel'] li[data-label='FISIOTERAPEUTA']")
        await page.wait_for_timeout(1000)
        
        print("Pulsando el botón 'Seleccionar' final para procesar resultados...")
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            await page.click("button[id*='btnBuscarLlamamientos']")
        
        print("Esperando la carga de datos en pantalla...")
        await page.wait_for_timeout(3000)

        # 3. PASO: EXTRACCIÓN DE FILAS
        print("Analizando HTML final...")
        html = await page.content()
        await browser.close()
        
        soup = BeautifulSoup(html, "html.parser")
        tablas = soup.find_all("table")
        
        if not tablas:
            print("Error: No se localizaron las tablas de resultados en el HTML final.")
            return

        lineas_mensaje = []
        datos_control = ""
        titulos_tablas = ["📋 *Nombramientos Ordinarios:*", "♿ *Cupo Personas con Discapacidad:*"]

        for i, tabla in enumerate(tablas):
            if i >= len(titulos_tablas):
                break
            
            # Filtramos las filas que realmente contienen celdas de datos (td), omitiendo las cabeceras
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
            print("Error: Tablas procesadas pero no se encontraron filas de datos numéricos.")
            return

        # 4. PASO: PERSISTENCIA Y ALERTA
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
            print("Notificación enviada con éxito a Telegram.")
        else:
            print("Sin novedades. Los datos coinciden con el registro guardado.")

if __name__ == "__main__":
    asyncio.run(consultar_llamamientos())
