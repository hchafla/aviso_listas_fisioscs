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
        print("Iniciando navegador...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES"
        )
        page = await context.new_page()
        
        # PASO 1: Entrar a la página inicial
        print(f"Abriendo Home: {url_base}")
        await page.goto(url_base, wait_until="networkidle")
        
        # PASO 2: Interactuar con el Bloque 3 (Llamamientos)
        print("Buscando el desplegable en el Bloque 3 (Llamamientos)...")
        # El tercer desplegable de la página corresponde al bloque 3 del vídeo
        desplegable_gerencia = page.locator(".ui-selectonemenu").nth(2)
        await desplegable_gerencia.click()
        await page.wait_for_timeout(800)
        
        print("Seleccionando Hospital Dr. Negrín...")
        await page.click("li:has-text('Hospital Universitario de Gran Canaria Doctor Negrín')")
        await page.wait_for_timeout(1000)
        
        print("Pulsando el primer botón 'Seleccionar' para ir a Categorías...")
        # Pulsamos el botón 'Seleccionar' que está dentro del bloque de llamamientos (el tercero de la página)
        boton_seleccionar_1 = page.locator("button:has-text('Seleccionar')").nth(2)
        
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            await boton_seleccionar_1.click()
            
        print("¡Redirección exitosa! Ya estamos en la página de Categorías.")
        await page.wait_for_timeout(1500)

        # PASO 3: Seleccionar la categoría FISIOTERAPEUTA
        print("Abriendo desplegable de Categorías...")
        # En esta nueva pantalla, el combo de categorías es el primero disponible
        await page.locator(".ui-selectonemenu").first.click()
        await page.wait_for_timeout(800)
        
        print("Seleccionando FISIOTERAPEUTA...")
        await page.click("li:has-text('FISIOTERAPEUTA')")
        await page.wait_for_timeout(1000)
        
        print("Pulsando el segundo botón 'Seleccionar' para ver los resultados...")
        # Pulsamos el botón Seleccionar de esta segunda pantalla para cargar los datos finales
        boton_seleccionar_2 = page.locator("button:has-text('Seleccionar')").first
        
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            await boton_seleccionar_2.click()
            
        print("Esperando renderizado de las tablas de datos...")
        await page.wait_for_timeout(2500)

        # PASO 4: Analizar las tablas de resultados finales
        print("Extrayendo información de las tablas...")
        html = await page.content()
        await browser.close()
        
        soup = BeautifulSoup(html, "html.parser")
        tablas = soup.find_all("table")
        
        if not tablas:
            print("Error: No se localizaron las tablas en la pantalla final.")
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
            print("Las tablas no contenían datos de filas válidos.")
            return

        # PASO 5: Comprobación de cambios y envío de alerta
        estado_anterior = ""
        if os.path.exists(FICHERO_ESTADO):
            with open(FICHERO_ESTADO, "r", encoding="utf-8") as f:
                estado_anterior = f.read().strip()

        if datos_control != estado_anterior:
            with open(FICHERO_ESTADO, "w", encoding="utf-8") as f:
                f.write(datos_control)
                
            mensaje_final = "🔄 *SCS: ACTUALIZACIÓN DE LLAMAMIENTOS*\n"
            mensaje_final += "🏥 _Hospital Dr. Negrín — FISIOTERAPEUTA_\n\n"
            mensaje_final += "\n".join(lineas_mensaje)
            mensaje_final += f"\n🔗 [Verificar en la Web]({url_base})"
            
            enviar_telegram(mensaje_final)
            print("¡Éxito! Notificación enviada a Telegram.")
        else:
            print("Sin cambios en los listados de llamamientos.")

if __name__ == "__main__":
    asyncio.run(consultar_llamamientos())
