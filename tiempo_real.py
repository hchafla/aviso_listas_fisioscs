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
        print("Lanzando navegador virtual...")
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        # 1. Ir a la página de inicio para abrir sesión legítima
        print(f"Conectando a la Home: {url_base}")
        await page.goto(url_base, wait_until="networkidle", timeout=30000)
        
        # 2. Hacer clic en el enlace o pestaña que lleva a los Últimos Llamamientos
        # Buscamos el texto literal del menú basándonos en la miga de pan de tu captura
        print("Navegando a la sección de Últimos Llamamientos...")
        link_llamamientos = page.get_by_role("link", name="Últimos llamamientos", exact=False)
        
        if await link_llamamientos.count() > 0:
            async with page.expect_navigation(wait_until="networkidle", timeout=20000):
                await link_llamamientos.first.click()
        else:
            # Si no encuentra el enlace por texto, forzamos la url ahora que la cookie está fijada
            print("Enlace no detectado por texto. Forzando navegación directa por sub-url...")
            async with page.expect_navigation(wait_until="networkidle", timeout=20000):
                await page.goto("https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/categorias.xhtml")

        # 3. Esperar a que el formulario esté pintado en pantalla
        print("Esperando renderizado del formulario...")
        await page.wait_for_selector("div[id='formulario:gerenciaUNSOM']", timeout=20000)
        
        # 4. Seleccionar la Gerencia (Negrín)
        print("Abriendo desplegable de Gerencias...")
        await page.click("div[id='formulario:gerenciaUNSOM'] span.ui-selectonemenu-trigger")
        await page.wait_for_timeout(600)
        
        print("Seleccionando Hospital Dr. Negrín...")
        await page.click("div[id='formulario:gerenciaUNSOM_panel'] li[data-label='Hospital Universitario de Gran Canaria Doctor Negrín']")
        await page.wait_for_timeout(1200)

        # 5. Seleccionar la Categoría (FISIOTERAPEUTA)
        print("Abriendo desplegable de Categorías...")
        await page.click("div[id='formulario:categoriaUNSOM'] span.ui-selectonemenu-trigger")
        await page.wait_for_timeout(600)
        
        print("Seleccionando FISIOTERAPEUTA...")
        await page.click("div[id='formulario:categoriaUNSOM_panel'] li[data-label='FISIOTERAPEUTA']")
        await page.wait_for_timeout(1200)

        # 6. Clic en Buscar
        print("Pulsando botón de búsqueda...")
        async with page.expect_navigation(wait_until="networkidle", timeout=25000):
            await page.click("button[id='formulario:btnBuscarLlamamientos']")

        # 7. Capturar los resultados finales
        print("Procesando tablas de resultados...")
        html = await page.content()
        await browser.close()
        
        soup = BeautifulSoup(html, "html.parser")
        tablas = soup.find_all("table")
        
        if not tablas:
            print("Error: No se localizaron las tablas tras la búsqueda.")
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
            print("Estructura de tablas vacía de contenido indexable.")
            return

        # Lógica de persistencia de alertas
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
            print("Cambio guardado. Notificación enviada a Telegram.")
        else:
            print("Los datos coinciden exactamente con el último registro. Sin cambios.")

if __name__ == "__main__":
    asyncio.run(consultar_llamamientos())
