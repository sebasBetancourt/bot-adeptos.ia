"""
Browser Service — Stealth Playwright automation for LinkedIn.

Key anti-detection features:
  - Random delays between actions (human-like timing)
  - Smooth scrolling instead of instant jumps
  - Random mouse movements before clicks
  - Realistic viewport and user-agent
  - Extracts TEXT only (not HTML) to save costs

FIX: Browser is created fresh per-request to avoid NoneType errors
     from stale page/context references between Flask requests.
"""
import asyncio
import random
import os
import urllib.parse
from playwright.async_api import async_playwright


class BrowserService:
    """
    Each call to start() creates a FRESH browser instance.
    This avoids NoneType errors from stale page references
    between separate Flask/WhatsApp requests.
    """

    def __init__(self):
        self.playwright = None
        self.context = None
        self.page = None

    # ==========================================================
    #  STEALTH HELPERS — Make the bot look human
    # ==========================================================

    async def _human_delay(self, min_s=1.0, max_s=3.0):
        """Random delay to simulate human reading/thinking time."""
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _human_scroll(self, distance=300):
        """Smooth scroll down like a human (not instant jump)."""
        if not self.page:
            return
        steps = random.randint(3, 6)
        step_distance = distance // steps
        for _ in range(steps):
            await self.page.evaluate(f"window.scrollBy(0, {step_distance})")
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def _human_mouse_move(self):
        """Random mouse movement to simulate a real user."""
        if not self.page:
            return
        x = random.randint(100, 900)
        y = random.randint(100, 600)
        await self.page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.2, 0.5))

    # ==========================================================
    #  BROWSER LIFECYCLE — Fresh per request
    # ==========================================================

    async def start(self, headless: bool = False):
        """
        Starts a FRESH browser instance every time.
        Closes any previous instance first to prevent zombie processes.
        """
        # Close any previous instance first
        await self.close()

        user_data_dir = os.path.join(os.getcwd(), "playwright_session")

        # Verify the session directory exists
        if not os.path.isdir(user_data_dir):
            os.makedirs(user_data_dir, exist_ok=True)
            print(f"--- [BROWSER] Creado directorio de sesión: {user_data_dir} ---")
            print("--- [BROWSER] ⚠️ No hay sesión de LinkedIn guardada. ---")
            print("--- [BROWSER] Ejecuta: python login_linkedin.py ---")

        self.playwright = await async_playwright().start()

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        # Get or create a page
        self.page = (
            self.context.pages[0]
            if self.context.pages
            else await self.context.new_page()
        )

        # Verify page is usable
        if self.page is None:
            raise RuntimeError("Playwright no pudo crear una página. Cierra Chrome manualmente y reintenta.")

        # Remove webdriver flag (anti-detection)
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)

        print("--- [BROWSER] ✅ Navegador stealth iniciado ---")

    # ==========================================================
    #  AUTO-LOGIN — Adapts to ANY LinkedIn login variant
    # ==========================================================

    async def _auto_login(self, redirect_url: str = "") -> bool:
        """
        Smart login that adapts to whatever LinkedIn page is showing.
        LinkedIn has MULTIPLE login variants:
          1. Standard form: #username + #password
          2. Session form: email pre-filled, only password needed
          3. Authwall: "Join LinkedIn" page with a small sign-in link
          4. Checkpoint: verification/CAPTCHA page
        """
        from src.config import Config

        email = Config.LINKEDIN_EMAIL
        password = Config.LINKEDIN_PASSWORD

        if not email or not password:
            print("--- [BROWSER] ❌ No hay credenciales en .env ---")
            return False

        print(f"--- [BROWSER] 🔐 Auto-login con: {email[:15]}... ---")

        try:
            # Take screenshot to see what we're dealing with
            await self.page.screenshot(path="login_page_debug.png")
            print("--- [BROWSER] 📸 Screenshot guardado: login_page_debug.png ---")

            await self._human_delay(1.0, 2.0)

            # ---- STEP 1: Find and handle the email field ----
            email_filled = False

            # Try all possible email selectors
            email_selectors = [
                "#username",
                "input[name='session_key']",
                "input[type='email']",
                "input[autocomplete='username']",
                "input[name='email']",
            ]

            email_field = None
            for sel in email_selectors:
                email_field = await self.page.query_selector(sel)
                if email_field:
                    visible = await email_field.is_visible()
                    if visible:
                        print(f"--- [BROWSER] 📧 Campo email encontrado: {sel} ---")
                        break
                    email_field = None

            if email_field:
                # Check if email is already filled
                current_value = await email_field.input_value()
                if current_value and "@" in current_value:
                    print(f"--- [BROWSER] 📧 Email ya está puesto: {current_value[:15]}... ---")
                    email_filled = True
                else:
                    # Type email character by character
                    await self._human_mouse_move()
                    await email_field.click()
                    await self._human_delay(0.3, 0.7)
                    await email_field.fill("")
                    for char in email:
                        await self.page.keyboard.type(char, delay=random.randint(50, 150))
                    email_filled = True
                    print("--- [BROWSER] 📧 Email escrito ---")
                    await self._human_delay(0.5, 1.0)
            else:
                print("--- [BROWSER] ⚠️ No se encontró campo de email ---")
                # Maybe it's an authwall — look for a sign-in link
                sign_in_link = await self.page.query_selector("a[href*='login']")
                if sign_in_link:
                    print("--- [BROWSER] 🔗 Encontrado link de Sign In — haciendo click ---")
                    await sign_in_link.click()
                    await self._human_delay(2.0, 3.0)
                    # Retry recursively (now should be on actual login page)
                    return await self._auto_login(redirect_url)

            # ---- STEP 2: Find and fill password ----
            password_selectors = [
                "#password",
                "input[name='session_password']",
                "input[type='password']",
                "input[autocomplete='current-password']",
            ]

            password_field = None
            for sel in password_selectors:
                password_field = await self.page.query_selector(sel)
                if password_field:
                    visible = await password_field.is_visible()
                    if visible:
                        print(f"--- [BROWSER] 🔑 Campo password encontrado: {sel} ---")
                        break
                    password_field = None

            if password_field:
                await password_field.click()
                await self._human_delay(0.3, 0.5)
                await password_field.fill("")
                for char in password:
                    await self.page.keyboard.type(char, delay=random.randint(60, 180))
                print("--- [BROWSER] 🔑 Password escrito ---")
                await self._human_delay(0.5, 1.0)
            else:
                print("--- [BROWSER] ⚠️ No se encontró campo de password ---")
                # Maybe email-first flow: submit email, then password appears
                if email_filled:
                    await self.page.keyboard.press("Enter")
                    await self._human_delay(2.0, 4.0)
                    # Try again for password
                    for sel in password_selectors:
                        password_field = await self.page.query_selector(sel)
                        if password_field and await password_field.is_visible():
                            await password_field.click()
                            for char in password:
                                await self.page.keyboard.type(char, delay=random.randint(60, 180))
                            print("--- [BROWSER] 🔑 Password escrito (2do intento) ---")
                            break

            # ---- STEP 3: Submit ----
            await self._human_delay(0.5, 1.0)

            submit_selectors = [
                "button[type='submit']",
                "button[data-litms-control-urn*='login-submit']",
                "button.btn__primary--large",
                "#organic-div button",
            ]

            submitted = False
            for sel in submit_selectors:
                btn = await self.page.query_selector(sel)
                if btn and await btn.is_visible():
                    box = await btn.bounding_box()
                    if box:
                        await self.page.mouse.move(
                            box["x"] + box["width"] / 2 + random.randint(-5, 5),
                            box["y"] + box["height"] / 2 + random.randint(-3, 3),
                        )
                        await self._human_delay(0.3, 0.6)
                    await btn.click()
                    submitted = True
                    print(f"--- [BROWSER] 🖱️ Submit clickeado: {sel} ---")
                    break

            if not submitted:
                await self.page.keyboard.press("Enter")
                print("--- [BROWSER] ⏎ Submit por Enter ---")

            print("--- [BROWSER] ⏳ Esperando respuesta de LinkedIn... ---")
            await self._human_delay(4.0, 7.0)

            # ---- STEP 4: Check result ----
            current_url = self.page.url

            # Handle verification/CAPTCHA
            if any(x in current_url for x in ["checkpoint", "challenge", "security", "verify"]):
                print("--- [BROWSER] ⚠️ LinkedIn pide verificación ---")
                print("--- [BROWSER] 👉 COMPLETA LA VERIFICACIÓN EN EL NAVEGADOR (90 seg) ---")
                await self.page.screenshot(path="verification_page.png")
                for i in range(18):  # 90 seconds
                    await asyncio.sleep(5)
                    url = self.page.url
                    if any(x in url for x in ["feed", "search", "mynetwork"]):
                        print("--- [BROWSER] ✅ Verificación completada ---")
                        break
                    if i % 3 == 0:
                        print(f"--- [BROWSER] ⏳ Esperando verificación... ({(i+1)*5}s) ---")
                else:
                    print("--- [BROWSER] ❌ Tiempo de verificación agotado (90s) ---")
                    return False

            # Check if we're logged in
            current_url = self.page.url
            if any(x in current_url for x in ["feed", "mynetwork", "search", "messaging"]):
                print("--- [BROWSER] ✅ Login exitoso ---")

                if redirect_url:
                    await self._human_delay(1.0, 2.0)
                    await self.page.goto(redirect_url, wait_until="domcontentloaded")
                    await self._human_delay(2.0, 4.0)

                return True

            # Unknown state — take screenshot for debug
            await self.page.screenshot(path="login_result_debug.png")
            print(f"--- [BROWSER] ⚠️ Estado desconocido: {current_url[:80]} ---")
            print("--- [BROWSER] 📸 Screenshot: login_result_debug.png ---")
            return False

        except Exception as e:
            print(f"--- [BROWSER] ❌ Error en auto-login: {e} ---")
            await self.page.screenshot(path="login_error_debug.png")
            return False

    # ==========================================================
    #  LINKEDIN NAVIGATION
    # ==========================================================

    async def search_leads(self, query: str) -> bool:
        """
        Navigates to LinkedIn search results for people.
        Auto-logs in if session expired. Uses human-like behavior.
        """
        if not self.page:
            print("--- [BROWSER] ❌ Error: page es None ---")
            return False

        encoded_query = urllib.parse.quote(query)
        search_url = (
            f"https://www.linkedin.com/search/results/people/"
            f"?keywords={encoded_query}&origin=GLOBAL_SEARCH_HEADER"
        )

        print(f"--- [BROWSER] Buscando: {query} ---")

        # Navigate with human-like timing
        await self._human_delay(1.0, 2.0)
        await self.page.goto(search_url, wait_until="domcontentloaded")

        # Wait a bit like a human would
        await self._human_delay(2.0, 4.0)

        # Check if we need to login
        current_url = self.page.url
        if "login" in current_url or "authwall" in current_url or "checkpoint" in current_url:
            print("--- [BROWSER] 🔐 LinkedIn requiere login — auto-login iniciado ---")
            logged_in = await self._auto_login(search_url)
            if not logged_in:
                return False

        # Scroll down slowly to trigger lazy loading
        await self._human_mouse_move()
        await self._human_scroll(400)
        await self._human_delay(1.5, 3.0)
        await self._human_scroll(300)
        await self._human_delay(1.0, 2.0)

        # Try multiple selectors (LinkedIn changes them)
        selectors = [
            ".reusable-search__result-container",
            "[data-chameleon-result-urn]",
            ".search-results-container li",
            "div.entity-result",
        ]

        for selector in selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=8000)
                print(f"--- [BROWSER] ✅ Resultados encontrados con: {selector} ---")
                return True
            except Exception:
                continue

        print("--- [BROWSER] ⚠️ No se encontraron resultados con ningún selector ---")
        return False

    # ==========================================================
    #  TEXT EXTRACTION (not HTML — 25x cheaper for RAG)
    # ==========================================================

    async def extract_raw_text_from_results(self, max_results: int = 10) -> tuple:
        """
        Extracts CLEAN TEXT (not HTML) from LinkedIn search results.
        Also extracts profile URLs from href attributes.

        Returns: (raw_texts: list[str], profile_urls: list[str])
        """
        raw_texts = []
        profile_urls = []

        if not self.page:
            return raw_texts, profile_urls

        # Try multiple selectors for robustness
        selectors = [
            ".reusable-search__result-container",
            "[data-chameleon-result-urn]",
            "div.entity-result",
        ]

        containers = []
        for selector in selectors:
            containers = await self.page.query_selector_all(selector)
            if containers:
                break

        if not containers:
            print("--- [BROWSER] No containers found ---")
            return raw_texts, profile_urls

        # Extract text from each container (human-like scrolling between results)
        for i, container in enumerate(containers[:max_results]):
            try:
                # Get CLEAN TEXT — no HTML, no tags, just readable text
                text = await container.inner_text()
                text = text.strip()

                if text and len(text) > 10:
                    raw_texts.append(text)

                # Try to get profile URL
                link = await container.query_selector("a[href*='/in/']")
                if link:
                    href = await link.get_attribute("href")
                    if href:
                        clean_url = href.split("?")[0]
                        profile_urls.append(clean_url)
                    else:
                        profile_urls.append("")
                else:
                    profile_urls.append("")

                # Small random scroll between results (looks human)
                if i % 3 == 2:
                    await self._human_scroll(200)
                    await self._human_delay(0.5, 1.5)

            except Exception as e:
                print(f"--- [BROWSER] Error extrayendo resultado {i}: {e} ---")

        print(f"--- [BROWSER] Extraídos {len(raw_texts)} textos crudos ---")
        return raw_texts, profile_urls

    # ==========================================================
    #  DEEP INVESTIGATION & CONNECTION
    # ==========================================================

    async def visit_profile_and_connect(self, profile_url: str, message: str = "") -> dict:
        """
        Navigates to a profile, extracts 'About' info, and sends a connection request.
        """
        if not self.page:
            return {"status": "error", "error": "Browser not started"}

        print(f"--- [BROWSER] Visitando perfil: {profile_url} ---")
        
        try:
            # Navigate to profile
            await self._human_delay(2.0, 4.0)
            await self.page.goto(profile_url, wait_until="domcontentloaded")
            await self._human_delay(3.0, 5.0)

            # Scroll to look human and load lazy content
            await self._human_scroll(500)
            await self._human_delay(1.0, 2.0)

            # Extract basic investigation info (About section typically)
            about_text = ""
            about_selector = "div.display-flex.ph5.pv3 span.break-words" # Common selector
            about_el = await self.page.query_selector(about_selector)
            if about_el:
                about_text = await about_el.inner_text()
                print(f"--- [BROWSER] Info extraída: {about_text[:50]}... ---")

            # Take screenshot for debug
            await self.page.screenshot(path="profile_visit_debug.png")

            # --- SEARCH FOR CONNECT BUTTON ---
            # 1. Direct "Connect" button
            connect_btn = await self.page.query_selector("button.pvs-profile-actions__action.artdeco-button--primary:has-text('Connect')")
            
            # 2. If not found, try "More..." menu
            if not connect_btn:
                more_btn = await self.page.query_selector("button.artdeco-dropdown__trigger:has-text('More')")
                if more_btn:
                    await more_btn.click()
                    await self._human_delay(1.0, 2.0)
                    connect_btn = await self.page.query_selector("div.artdeco-dropdown__item:has-text('Connect')")

            if connect_btn:
                print("--- [BROWSER] 🖱️ Botón 'Conectar' encontrado ---")
                await connect_btn.click()
                await self._human_delay(1.5, 2.5)

                # Send with message if provided
                if message:
                    add_note_btn = await self.page.query_selector("button:has-text('Add a note')")
                    if add_note_btn:
                        await add_note_btn.click()
                        await self._human_delay(1.0, 2.0)
                        
                        # Type message (human-like)
                        textarea = await self.page.query_selector("textarea[name='message']")
                        if textarea:
                            await textarea.fill("")
                            for char in message[:300]: # LinkedIn limit
                                await self.page.keyboard.type(char, delay=random.randint(40, 120))
                            
                            await self._human_delay(1.0, 2.0)
                            send_btn = await self.page.query_selector("button:has-text('Send')")
                            if send_btn:
                                # await send_btn.click() # SAFETY: Commented out for now until user specifically asks to ACTUALLY send
                                print("--- [BROWSER] ✅ Solicitud con mensaje preparada ---")
                
                return {"status": "success", "info": about_text}
            else:
                print("--- [BROWSER] ⚠️ No se encontró botón de conexión (¿Ya conectado?) ---")
                return {"status": "skipped", "info": about_text}

        except Exception as e:
            print(f"--- [BROWSER] Error en visita/conexión: {e} ---")
            return {"status": "error", "error": str(e)}

    # ==========================================================
    #  UTILITIES
    # ==========================================================


    async def take_screenshot(self, path: str) -> str:
        """Takes a screenshot of the current page."""
        if self.page:
            await self.page.screenshot(path=path)
        return path

    async def close(self):
        """Closes the browser gracefully — prevents zombie processes."""
        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            print(f"--- [BROWSER] Error cerrando context: {e} ---")

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"--- [BROWSER] Error cerrando playwright: {e} ---")

        self.playwright = None
        self.context = None
        self.page = None
