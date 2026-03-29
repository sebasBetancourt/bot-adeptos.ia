from typing import Dict
import re
import os
from src.config import Config
from .state import AgentState
from src.services.browser_service import BrowserService


def _extract_query_from_text(text: str) -> str:
    """
    Smart regex fallback to extract a LinkedIn search query from a WhatsApp message.
    Works without any LLM connection.
    """
    # Remove common command words at the start
    clean = re.sub(
        r'^(busca(me)?|encuéntrame|encuentrame|necesito|quiero|búscame|buscar)\s+',
        '', text, flags=re.IGNORECASE
    ).strip()
    # Remove trailing phrases
    clean = re.sub(r'\s+(en whatsapp|por whatsapp|ahora|ya|por favor|porfavor)$', '', clean, flags=re.IGNORECASE).strip()
    return clean if clean else text


class MarketingNodes:
    """
    Encapsulates all LangGraph nodes for the AI Marketing Agent.
    The LLM is initialized lazily — if the API key is invalid or
    the account has no credits, the bot falls back to smart regex
    extraction and ALWAYS continues to the browser automation step.
    """

    def __init__(self):
        self._llm = None  # Lazy initialization
        self.browser_service = BrowserService()

    def _get_llm(self):
        """Initializes the LLM client on first use."""
        if self._llm is None:
            try:
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model="claude-sonnet-4-20250514",
                    api_key=Config.ANTHROPIC_API_KEY
                )
                print(f"--- [LLM] Claude Sonnet 4 inicializado correctamente. ---")
            except Exception as e:
                print(f"--- [LLM] Error al inicializar Claude: {e} ---")
        return self._llm

    async def _safe_llm_invoke(self, prompt: str) -> str | None:
        """
        Calls the LLM safely. Returns None on ANY API error (401, 404, 400, etc.)
        so the calling node can fall back to regex extraction.
        """
        llm = self._get_llm()
        if llm is None:
            return None
        try:
            response = await llm.ainvoke([("human", prompt)])
            return response.content.strip().replace('"', '')
        except Exception as e:
            print(f"--- [LLM] API error ({type(e).__name__}): {e} ---")
            print("--- [LLM] Usando extracción manual como respaldo. ---")
            return None

    async def receive_order_node(self, state: AgentState) -> Dict:
        """
        Node 1: Extracts the LinkedIn search query from the WhatsApp message.
        Uses Claude Sonnet 3.5 when available, regex fallback otherwise.
        """
        print("--- [NODE] RECEPCIÓN DE ORDEN ---")
        user_order = state.get("last_order_raw", "")
        print(f"Orden recibida: {user_order}")

        # Build prompt for smart extraction
        prompt = (
            f"Eres un asistente de ventas. Del mensaje de WhatsApp: '{user_order}', "
            f"extrae SOLO los términos de búsqueda para LinkedIn. "
            f"Ejemplo: 'gerentes de marketing en Colombia'. Responde ONLY con los términos."
        )

        search_query = await self._safe_llm_invoke(prompt)

        if not search_query:
            # Regex fallback — always works, no API needed
            search_query = _extract_query_from_text(user_order)
            print(f"--- [FALLBACK] Consulta extraída por regex: '{search_query}' ---")
        else:
            print(f"--- [LLM] Consulta extraída por Claude: '{search_query}' ---")

        return {
            "messages": [("ai", f"Entendido. Buscando: '{search_query}' en LinkedIn.")],
            "last_order_raw": search_query,
        }

    async def navigate_playwright_node(self, state: AgentState) -> Dict:
        """
        Node 2: Opens the browser, navigates to LinkedIn and extracts leads.
        """
        print("--- [NODE] NAVEGACIÓN PLAYWRIGHT ---")
        search_query = state.get("last_order_raw", "")

        # Start the browser (headless=False so you can watch it work)
        await self.browser_service.start(headless=False)

        # Perform the search on LinkedIn
        found = await self.browser_service.search_leads(search_query)

        if found:
            leads = await self.browser_service.extract_leads_from_page()
            print(f"Leads encontrados: {len(leads)}")

            screenshot_path = "search_results.png"
            await self.browser_service.take_screenshot(screenshot_path)

            lead_summary = "\n".join([f"- {l['name']} ({l['headline']})" for l in leads])
            ai_message = (
                f"✅ Búsqueda completada para '{search_query}'.\n"
                f"Encontré {len(leads)} leads:\n{lead_summary}"
            )

            return {
                "messages": [("ai", ai_message)],
                "screenshot_path": screenshot_path,
                "current_leads": leads,
            }

        return {
            "messages": [("ai", f"⚠️ No encontré resultados para '{search_query}' o LinkedIn requiere login.")]
        }


# Singleton — instantiated once at startup
marketing_nodes = MarketingNodes()
