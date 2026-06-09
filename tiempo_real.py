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
        
        # PASO 2: Interactuar con el Bloque 3 (Llamamientos) usando identificadores del DOM
        print("Localizando el bloque 3 de Últimos Llamamientos...")
        
        # Localizamos el contenedor del combo del bloque 3. 
        # En PrimeFaces suele ser el elemento previo al panel flotante o comparte estructura.
        # Buscamos el div del selector de gerencia dentro de la sección de llamamientos.
        selector_gerencia = page.locator("div[id*='gerenciaUNSOM']").first
        if await selector_gerencia.count() == 0:
            selector_gerencia = page.locator("div[id*='j_idt43']").first

        print("Abriendo el menú de Gerencia del Bloque 3...")
        await selector_gerencia.click()
        await page.wait_for_timeout(1000)
        
        print("Seleccionando Hospital Dr. Negrín...")
        # Hacemos clic en la opción del Negrín dentro del panel explícito que vimos en tus capturas
        await page.click("div[id*='gerenciaUNSOM_panel'] li[data-label='Hospital Universitario de Gran Canaria Doctor Negrín']")
        await page.wait_for_timeout(1000)
        
        print("Pulsando el botón 'Seleccionar' del bloque 3...")
        # Buscamos el botón 'Seleccionar' que ejecute la acción del formulario de llamamientos
        boton_seleccionar_1 = page.locator("button[id*='btnSeleccionarGerenciaUNSOM']").first
        if await boton_seleccionar_1.count() == 0:
            # Si el ID cambia, usamos el botón 'Seleccionar' que esté más cerca del texto del bloque 3
            boton_seleccionar_1 = page.locator("text=Seleccionar").nth(2)
        
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            await boton_seleccionar_1.click()
            
        print("¡Redirección exitosa! Procesando página de Categorías...")
        await page.wait_for_timeout(2000)

        # PASO 3: Seleccionar la categoría FISIOTERAPEUTA
        print("Abriendo desplegable de Categorías...")
        # En la nueva página (categorias.xhtml), el selector de categoría usará la marca UNSOM
        selector_categoria = page.locator("div[id*='categoriaUNSOM']").first
        await selector_categoria.click()
        await page.wait_for_timeout(1000)
        
        print("Seleccionando FISIOTERAPEUTA...")
        await page.click("div[id*='categoriaUNSOM_panel'] li[data-label='FISIOTERAPEUTA']")
        await page.wait_for_timeout(1000)
        
        print("Pulsando el botón 'Seleccionar' final para ver resultados...")
        boton_seleccionar_2 = page.locator("button[id*='btnBuscarLlamamientos']").first
        if await boton_seleccionar_2.count() == 0:
            boton_seleccionar_2 = page.locator("text=Seleccionar").first
        
        async with page.expect_navigation(wait_until="networkidle", timeout=20000):
            await boton_seleccionar_2.click()
            
        print("Esperando tablas de resultados...")
        await page.wait_for_timeout(3000)

        # PASO 4: Analizar las tablas de resultados finales
        print("Extrayendo información de las tablas...")
        html = await page.content()
        await browser.close()
        
        soup = BeautifulSoup(html, "html.parser")
        tablas = soup.find_all("table")
        
        if not tablas:
            print("Error: No se localizaron las tablas de resultados.")
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
            print("Tablas sin datos legibles.")
            return

        # PASO 5: Control de cambios
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
            print("Notificación enviada a Telegram.")
        else:
            print("Sin cambios detectados.")

if __name__ == "__main__":
    asyncio.run(consultar_llamamientos())
