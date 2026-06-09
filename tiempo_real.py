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
        
        print(f"Conectando a la Home: {url_base}")
        await page.goto(url_base, wait_until="networkidle", timeout=30000)
        
        # PASO CRÍTICO: Localizar y pulsar la pestaña o botón de "Últimos llamamientos"
        # para que el servidor JSF transmute la interfaz al formulario UNSOM
        print("Buscando el botón de cambio a 'Últimos llamamientos'...")
        
        # Intentamos por texto en cualquier elemento interactivo (enlace, botón, pestaña)
        pestana = page.get_by_text("Últimos llamamientos", exact=False)
        
        if await pestana.count() > 0:
            print("Pestaña localizada. Pulsando para cambiar de formulario...")
            await pestana.first.click()
            await page.wait_for_timeout(2000) # Tiempo para que PrimeFaces refresque el DOM via Ajax
        else:
            print("Aviso: No se localizó texto explícito. Intentando clic por selectores comunes de menú...")
            # Alternativa por si es un elemento de lista o menú de PrimeFaces
            await page.click("text=Últimos llamamientos")
            await page.wait_for_timeout(2000)

        # 3. Esperar a que el formulario UNSOM esté pintado en pantalla
        print("Comprobando si el formulario de llamamientos se ha renderizado...")
        # Buscamos el contenedor genérico del formulario si el ID estricto falla
        await page.wait_for_selector("form#formulario", timeout=20000)
        
        # Forzamos una comprobación de selectores disponibles para depurar si vuelve a fallar
        html_actual = await page.content()
        if "gerenciaUNSOM" not in html_actual:
            print("El formulario cambió pero no es el UNSOM esperado. Intentando forzar selectores estándar...")
            # Si no ha mutado el ID, es que usa el mismo contenedor para ambos paneles
            id_prefix = "formulario:gerenciaSOM" if "gerenciaSOM" in html_actual else "formulario:gerencia"
        else:
            id_prefix = "formulario:gerenciaUNSOM"

        print(f"Usando prefijo de componentes: {id_prefix}")
        cat_prefix = id_prefix.replace("gerencia", "categoria")

        # 4. Seleccionar la Gerencia (Negrín)
        print("Abriendo desplegable de Gerencias...")
        await page.click(f"div[id='{id_prefix}'] span.ui-selectonemenu-trigger")
        await page.wait_for_timeout(800)
        
        print("Seleccionando Hospital Dr. Negrín...")
        await page.click(f"div[id='{id_prefix}_panel'] li[data-label='Hospital Universitario de Gran Canaria Doctor Negrín']")
        await page.wait_for_timeout(1500)

        # 5. Seleccionar la Categoría (FISIOTERAPEUTA)
        print("Abriendo desplegable de Categorías...")
        await page.click(f"div[id='{cat_prefix}'] span.ui-selectonemenu-trigger")
        await page.wait_for_timeout(800)
        
        print("Seleccionando FISIOTERAPEUTA...")
        await page.click(f"div[id='{cat_prefix}_panel'] li[data-label='FISIOTERAPEUTA']")
        await page.wait_for_timeout(1500)

        # 6. Clic en Buscar
        print("Pulsando botón de búsqueda...")
        # Buscamos el botón de buscar dentro de ese formulario mutado
        boton_buscar = page.locator("button[id*='btnBuscar']")
        await boton_buscar.first.click()
        await page.wait_for_timeout(3000) # Esperamos el refresco de las tablas de datos

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
    import asyncio
    asyncio.run(consultar_llamamientos())
