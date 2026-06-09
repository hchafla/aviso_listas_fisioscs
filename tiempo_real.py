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
        
        print(f"Abriendo Home: {url_base}")
        await page.goto(url_base, wait_until="networkidle")
        
        print("Pulsando en 'Últimos llamamientos'...")
        await page.click("text=Últimos llamamientos")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)

        # PASO 1: SELECCIÓN DE GERENCIA (Pantalla Inicial)
        print("Abriendo el menú de Gerencia...")
        # Hacemos clic en el primer (y único) desplegable disponible en esta pantalla
        await page.locator(".ui-selectonemenu").first.click()
        await page.wait_for_timeout(800)
        
        print("Seleccionando Hospital Dr. Negrín y esperando recarga de página...")
        # Al hacer clic en la opción, el navegador DEBE esperar una recarga/navegación automática
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            await page.click("li:has-text('Hospital Universitario de Gran Canaria Doctor Negrín')")
        
        print("¡Primera recarga completada con éxito!")
        await page.wait_for_timeout(2000)

        # PASO 2: SELECCIÓN DE CATEGORÍA (Nueva Pantalla)
        print("Buscando el nuevo selector de Categoría en la página cargada...")
        # En esta nueva pantalla, el desplegable de categorías debería estar listo
        await page.locator(".ui-selectonemenu").first.click()
        await page.wait_for_timeout(800)
        
        print("Seleccionando FISIOTERAPEUTA...")
        await page.click("li:has-text('FISIOTERAPEUTA')")
        await page.wait_for_timeout(1500)

        # PASO 3: BOTÓN BUSCAR
        print("Pulsando el botón Buscar final...")
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            await page.click("button:has-text('Buscar')")
        
        print("Esperando la carga de las tablas de resultados...")
        await page.wait_for_timeout(3000)

        # PASO 4: EXTRACCIÓN DE DATOS
        print("Analizando resultados finales...")
        html = await page.content()
        await browser.close()
        
        soup = BeautifulSoup(html, "html.parser")
        tablas = soup.find_all("table")
        
        if not tablas:
            print("Error: No se encontró ninguna tabla de resultados. Comprueba si el botón Buscar falló.")
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
            print("Tablas detectadas pero vacías por dentro.")
            return

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
            print("Cambio o inicio detectado. Mensaje enviado a Telegram.")
        else:
            print("Sin novedades en los llamamientos.")

if __name__ == "__main__":
    asyncio.run(consultar_llamamientos())
