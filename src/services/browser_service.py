import asyncio
from playwright.async_api import async_playwright
import os

class BrowserService:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def start(self, headless: bool = False):
        """
        Starts the browser instance with a persistent context.
        """
        self.playwright = await async_playwright().start()
        
        # Use a persistent context directory
        user_data_dir = os.path.join(os.getcwd(), "playwright_session")
        
        # Point to the session.json in the root if it exists
        storage_state = "session.json" if os.path.exists("session.json") else None
        
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def navigate_to_linkedin(self):
        """
        Navigates to LinkedIn login/search.
        """
        await self.page.goto("https://www.linkedin.com")
        # Check if we are logged in or at login wall
        return "LinkedIn Home reached"

    async def search_leads(self, query: str):
        """
        Performs a search for people on LinkedIn.
        """
        # Encode query for URL
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_query}&origin=GLOBAL_SEARCH_HEADER"
        
        print(f"Buscando: {query} en {search_url}")
        await self.page.goto(search_url)
        
        # Wait for results to load
        try:
            await self.page.wait_for_selector(".reusable-search__result-container", timeout=10000)
            return True
        except Exception as e:
            print(f"Error esperando resultados: {e}")
            return False

    async def extract_leads_from_page(self):
        """
        Extracts basic lead info from the current search results page.
        """
        leads = []
        # Find all result containers
        containers = await self.page.query_selector_all(".reusable-search__result-container")
        
        for container in containers[:5]: # Take first 5 for now
            try:
                # Name and Profile Link usually in a span/a within the title
                name_elem = await container.query_selector(".entity-result__title-text a")
                if name_elem:
                    name_full = await name_elem.inner_text()
                    name = name_full.split("\n")[0].strip() # Clean up "Degree of connection"
                    profile_url = await name_elem.get_attribute("href")
                    
                    # Headline
                    headline_elem = await container.query_selector(".entity-result__primary-subtitle")
                    headline = await headline_elem.inner_text() if headline_elem else "Sin titular"
                    
                    leads.append({
                        "name": name,
                        "profile_url": profile_url,
                        "headline": headline.strip()
                    })
            except Exception as e:
                print(f"Error extrayendo un lead: {e}")
                
        return leads

    async def take_screenshot(self, path: str):
        """
        Takes a screenshot of the current page.
        """
        await self.page.screenshot(path=path)
        return path

    async def close(self):
        """
        Closes the browser.
        """
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
