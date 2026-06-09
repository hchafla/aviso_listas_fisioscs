import asyncio
from playwright.async_api import async_playwright

async def auditar_pantalla():
    url_base = "https://www3.gobiernodecanarias.org/sanidad/scs/ConsultaSIGLE/index.xhtml"
    
    async with async_playwright() as p:
        print("Iniciando navegador en modo auditoría...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES"
        )
        page = await context.new_page()
        
        # Ajustamos una resolución estándar de pantalla de ordenador
        await page.set_viewport_size({"width": 1280, "height": 1024})
        
        print(f"Conectando a: {url_base}")
        await page.goto(url_base, wait_until="networkidle")
        await page.wait_for_timeout(3000) # Pausa de cortesía para renderizado
        
        # 1. Guardar captura de pantalla de lo que ve el robot
        print("Guardando captura de pantalla (evidencia_visual.png)...")
        await page.screenshot(path="evidencia_visual.png", full_page=True)
        
        # 2. Guardar el código HTML limpio para inspeccionar los IDs reales
        print("Guardando código HTML (codigo_fuente.txt)...")
        html = await page.content()
        with open("codigo_fuente.txt", "w", encoding="utf-8") as f:
            f.write(html)
            
        await browser.close()
        print("Auditoría finalizada. Archivos generados correctamente.")

if __name__ == "__main__":
    asyncio.run(auditar_pantalla())
