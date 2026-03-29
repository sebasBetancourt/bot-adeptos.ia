"""
Script para iniciar sesión en LinkedIn manualmente.
El navegador se abrirá y tú haces login con tu cuenta.
La sesión se guardará automáticamente en playwright_session/

USO:
    python login_linkedin.py

Después de hacer login, espera 5 segundos y cierra este script con Ctrl+C.
"""
import asyncio
import os
from playwright.async_api import async_playwright


async def login():
    print("=" * 50)
    print("  LOGIN MANUAL EN LINKEDIN")
    print("=" * 50)
    print()
    print("1. Se abrirá una ventana de Chrome")
    print("2. Inicia sesión con tu cuenta de LinkedIn")
    print("3. Una vez que veas tu Feed de LinkedIn, presiona ENTER aquí")
    print()

    playwright = await async_playwright().start()

    user_data_dir = os.path.join(os.getcwd(), "playwright_session")

    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=False,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )

    page = context.pages[0] if context.pages else await context.new_page()

    # Navegar a LinkedIn
    await page.goto("https://www.linkedin.com/login")
    print("🌐 Navegador abierto en LinkedIn...")
    print()

    # Esperar a que el usuario haga login
    input("👉 Cuando hayas iniciado sesión y veas tu Feed, presiona ENTER aquí...")

    # Verificar que estamos logueados
    current_url = page.url
    print(f"\nURL actual: {current_url}")

    if "feed" in current_url or "mynetwork" in current_url or "in/" in current_url:
        print("✅ ¡LOGIN EXITOSO! La sesión se ha guardado.")
        print("   El bot ahora podrá usar LinkedIn automáticamente.")
    else:
        print("⚠️  No parece que estés en el Feed. Intenta navegar manualmente al feed.")
        input("   Presiona ENTER cuando estés listo...")

    # Tomar screenshot de confirmación
    await page.screenshot(path="linkedin_logged_in.png")
    print("📸 Screenshot guardado: linkedin_logged_in.png")

    # Cerrar
    await context.close()
    await playwright.stop()

    print("\n🎉 ¡Listo! Ahora ejecuta: python -m src.app")
    print("   Y envía un mensaje de WhatsApp para buscar en LinkedIn.")


if __name__ == "__main__":
    asyncio.run(login())
