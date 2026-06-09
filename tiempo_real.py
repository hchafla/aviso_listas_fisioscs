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
    url_portal = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml"
    
    async with async_playwright() as p:
        print("Lanzando navegador virtual en segundo plano...")
        browser = await p.chromium.launch(headless=True)
        
        # Configuramos el contexto simulando un Chrome real en español
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        print(f"Conectando a: {url_portal}")
        await page.goto(url_portal, wait_until="networkidle", timeout=30000)
        
        # Esperamos a que los componentes de PrimeFaces estén listos en el DOM
        print("Esperando renderizado de controles PrimeFaces...")
        await page.wait_for_selector("form#formulario", timeout=15000)
        
        # PASO 1: Interactuar con el menú desplegable de Gerencia (UNSOM)
        print("Abriendo desplegable de Gerencias...")
        # Hacemos clic en el disparador del combo de PrimeFaces para la gerencia
        await page.click("div[id='formulario:gerenciaUNSOM'] span.ui-selectonemenu-trigger")
        await page.wait_for_timeout(500) # Pausa orgánica para que despliegue el HTML
        
        print("Seleccionando Hospital Dr. Negrín...")
        # Hacemos clic directamente en la opción del Negrín dentro del panel flotante
        await page.click("div[id='formulario:gerenciaUNSOM_panel'] li[data-label='Hospital Universitario de Gran Canaria Doctor Negrín']")
        await page.wait_for_timeout(1000) # Esperamos a que reaccione el script de la web

        # PASO 2: Interactuar con el menú de Categoría (UNSOM)
        print("Abriendo desplegable de Categorías...")
        await page.click("div[id='formulario:categoriaUNSOM'] span.ui-selectonemenu-trigger")
        await page.wait_for_timeout(500)
        
        print("Seleccionando FISIOTERAPEUTA...")
        await page.click("div[id='formulario:categoriaUNSOM_panel'] li[data-label='FISIOTERAPEUTA']")
        await page.wait_for_timeout(1000)

        # PASO 3: Clic en el botón Buscar Llamamientos
        print("Pulsando botón de búsqueda...")
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            await page.click("button[id='formulario:btnBuscarLlamamientos']")

        # PASO 4: Extraer el HTML final renderizado
        print("Extrayendo resultados...")
        html = await page.content()
        await browser.close()
        
        # Procesamiento clásico con BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        tablas = soup.find_all("table")
        
        if not tablas:
            print("Error: No se cargaron las tablas de resultados en el navegador emulado.")
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
            print("Estructura encontrada pero sin datos internos legibles.")
            return

        # Control de Persistencia
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
            mensaje_final += f"🔗 [Verificar Web]({url_portal})"
            
            enviar_telegram(mensaje_final)
            print("Cambio detectado. Notificación enviada a Telegram.")
        else:
            print("Sin novedades en las listas.")

if __name__ == "__main__":
    asyncio.run(consultar_llamamientos())
