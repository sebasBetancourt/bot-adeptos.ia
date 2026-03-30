"""
Marketing Agent Nodes — 6-node LangGraph pipeline.

Node 1: receive_order_node        — Extracts search query (Sonnet 4)
Node 2: navigate_playwright_node  — Stealth browser navigation (Playwright)
Node 3: extract_leads_rag_node    — Structures data with RAG
Node 4: classify_leads_node       — Assigns tier with Python rules ($0)
Node 5: save_leads_node           — Persists to SQLite (no duplicates)
Node 6: generate_messages_node    — Personalized cold outreach per lead (Sonnet 4)
"""
from typing import Dict
import re
import json
from src.config import Config
from .state import AgentState
from src.services.browser_service import BrowserService
from src.services.lead_repository import LeadRepository
from src.targeting import (
    ENTERPRISE_KEYWORDS,
    STARTER_KEYWORDS,
    SKIP_KEYWORDS,
)


def _extract_query_from_text(text: str) -> str:
    """Regex fallback to extract search terms from a WhatsApp message."""
    clean = re.sub(
        r'^(busca(me)?|encuéntrame|encuentrame|necesito|quiero|búscame|buscar)\s+',
        '', text, flags=re.IGNORECASE
    ).strip()
    clean = re.sub(
        r'\s+(en whatsapp|por whatsapp|ahora|ya|por favor|porfavor)$',
        '', clean, flags=re.IGNORECASE
    ).strip()
    return clean if clean else text


# ============================================================
#  RAG PROMPT — Optimized for Haiku 4.5 (short, precise)
# ============================================================

RAG_EXTRACTION_PROMPT = """Extract LinkedIn profiles from this text. Return a JSON array.

Fields per profile:
- nombre: Full name
- cargo: Current job title
- empresa: Current company
- ubicacion: City/Country if visible

TEXT:
{raw_text}

Return ONLY the JSON array. No explanation."""


# ============================================================
#  COLD EMAIL PROMPT — Personalized outreach per lead
#  Based on cold-email skill + Adeptos product context
# ============================================================

COLD_EMAIL_PROMPT = """You are an expert cold outreach writer for Adeptos (adeptos.ai).
Adeptos builds AI Revenue Systems — autonomous AI agents that handle sales conversations 24/7.

Write a SHORT LinkedIn connection message (max 300 chars) for this lead:
- Name: {nombre}
- Title: {cargo}
- Company: {empresa}
- Location: {ubicacion}
- Tier: {tier}

RULES:
1. Open with a specific observation about their company/role
2. Mention the revenue leak problem ($8,500/mo lost)
3. Include one proof point:
   - USA: "Helped Valvetronic reduce team from 20 to 5 while maintaining 8-figure sales"
   - Colombia: "Helped Proyectamos y Edificamos never miss a lead after hours"
4. End with low-friction CTA: "Worth a 15-min AI Audit?"
5. Sound like a peer, NOT a vendor. No "I hope this finds you well"
6. Use contractions. Be conversational.
7. If location contains Colombia/Bogotá/Medellín → write in SPANISH
8. If location contains USA/Miami/NY → write in ENGLISH

Write ONLY the message. No subject line. No explanation."""


class MarketingNodes:
    """
    Encapsulates all 5 LangGraph nodes for the AI Marketing Agent.

    Cost model:
      - Sonnet 4: Interprets user orders (creative task)
      - Haiku 4.5: Structures RAG data (mechanical task, 90% cheaper)
      - Python: Classification (free, $0)
    """

    def __init__(self):
        self._sonnet_llm = None      # Lazy — for user order interpretation
        self._haiku_client = None     # Lazy — for RAG extraction
        # browser_service is NOT created here — it's created fresh
        # inside navigate_playwright_node to avoid stale page references
        self.lead_repo = LeadRepository()

    # ----------------------------------------------------------
    #  LLM INITIALIZATION (lazy, separate clients for cost)
    # ----------------------------------------------------------

    def _get_sonnet_llm(self):
        """Initializes Sonnet 4 for creative tasks (order interpretation)."""
        if self._sonnet_llm is None:
            try:
                from langchain_anthropic import ChatAnthropic
                self._sonnet_llm = ChatAnthropic(
                    model="claude-sonnet-4-20250514",
                    api_key=Config.ANTHROPIC_API_KEY,
                )
                print("--- [LLM] Claude Sonnet 4 listo (órdenes). ---")
            except Exception as e:
                print(f"--- [LLM] Error inicializando Sonnet: {e} ---")
        return self._sonnet_llm

    def _get_haiku_client(self):
        """Initializes Anthropic SDK client for RAG (cheap extraction)."""
        if self._haiku_client is None:
            from anthropic import Anthropic
            self._haiku_client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            print("--- [LLM] Anthropic SDK listo (RAG). ---")
        return self._haiku_client

    async def _safe_sonnet_invoke(self, prompt: str) -> str | None:
        """Calls Sonnet 4 safely with fallback."""
        llm = self._get_sonnet_llm()
        if llm is None:
            return None
        try:
            response = await llm.ainvoke([("human", prompt)])
            return response.content.strip().replace('"', '')
        except Exception as e:
            print(f"--- [LLM] Sonnet error: {e} ---")
            return None

    def _haiku_extract(self, raw_text: str) -> list[dict]:
        """
        Uses Haiku (cheapest model) to structure raw LinkedIn text into JSON.
        Falls back to Sonnet if Haiku is unavailable.
        """
        client = self._get_haiku_client()
        prompt = RAG_EXTRACTION_PROMPT.format(raw_text=raw_text)

        # Try Haiku first (cheapest), then Sonnet as fallback
        models_to_try = [
            "claude-haiku-4-5-20250514",
            "claude-sonnet-4-20250514",
        ]

        for model in models_to_try:
            try:
                message = client.messages.create(
                    model=model,
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw_response = message.content[0].text.strip()

                # Parse JSON from response
                # Handle case where model wraps in ```json blocks
                if "```" in raw_response:
                    raw_response = raw_response.split("```")[1]
                    if raw_response.startswith("json"):
                        raw_response = raw_response[4:]

                leads = json.loads(raw_response)
                print(f"--- [RAG] Extraídos {len(leads)} perfiles con {model}. ---")
                return leads if isinstance(leads, list) else []

            except json.JSONDecodeError:
                print(f"--- [RAG] JSON inválido de {model}, intentando próximo... ---")
                continue
            except Exception as e:
                print(f"--- [RAG] Error con {model}: {type(e).__name__}: {str(e)[:80]} ---")
                continue

        print("--- [RAG] Todos los modelos fallaron. Retornando lista vacía. ---")
        return []

    # ==========================================================
    #  NODE 1: RECIBIR ORDEN (Sonnet 4)
    # ==========================================================

    async def receive_order_node(self, state: AgentState) -> Dict:
        """Extracts LinkedIn search query from WhatsApp message."""
        print("--- [NODE 1] RECEPCIÓN DE ORDEN ---")
        user_order = state.get("last_order_raw", "")
        print(f"Orden recibida: {user_order}")

        prompt = (
            f"Eres un asistente de ventas. Del mensaje: '{user_order}', "
            f"extrae SOLO los términos de búsqueda para LinkedIn. "
            f"Ejemplo: 'gerentes de marketing en Colombia'. "
            f"Responde SOLO con los términos."
        )

        search_query = await self._safe_sonnet_invoke(prompt)

        if not search_query:
            search_query = _extract_query_from_text(user_order)
            print(f"--- [FALLBACK] Query por regex: '{search_query}' ---")
        else:
            print(f"--- [SONNET] Query extraída: '{search_query}' ---")

        return {
            "messages": [("ai", f"🔍 Buscando: '{search_query}' en LinkedIn...")],
            "last_order_raw": search_query,
        }

    # ==========================================================
    #  NODE 2: NAVEGAR LINKEDIN (Playwright Stealth)
    # ==========================================================

    async def navigate_playwright_node(self, state: AgentState) -> Dict:
        """Opens browser, searches LinkedIn, extracts raw text."""
        print("--- [NODE 2] NAVEGACIÓN STEALTH ---")
        search_query = state.get("last_order_raw", "")

        # Create a FRESH browser instance for this request
        browser = BrowserService()

        try:
            # Start stealth browser
            await browser.start(headless=False)

            # Navigate and search
            found = await browser.search_leads(search_query)

            if not found:
                await browser.close()
                return {
                    "messages": [("ai", "⚠️ No encontré resultados o LinkedIn requiere login.")],
                    "raw_search_text": "",
                    "profile_urls": [],
                }

            # Extract RAW TEXT (not HTML!) — 25x cheaper
            raw_texts, profile_urls = await browser.extract_raw_text_from_results(max_results=10)

            # Take screenshot for reference
            screenshot_path = "search_results.png"
            await browser.take_screenshot(screenshot_path)

            # Combine texts for RAG processing
            combined_text = "\n---\n".join(raw_texts)

            print(f"--- [NODE 2] Extraídos {len(raw_texts)} bloques de texto ---")

            # Close browser after extraction
            await browser.close()

            return {
                "raw_search_text": combined_text,
                "profile_urls": profile_urls,
                "screenshot_path": screenshot_path,
            }

        except Exception as e:
            print(f"--- [NODE 2] ❌ Error en navegación: {e} ---")
            # ALWAYS close browser on error to prevent zombie processes
            try:
                await browser.close()
            except Exception:
                pass
            return {
                "messages": [("ai", f"⚠️ Error navegando LinkedIn: {str(e)[:100]}")],
                "raw_search_text": "",
                "profile_urls": [],
            }

    # ==========================================================
    #  NODE 3: EXTRACCIÓN RAG (Haiku 4.5 — más barato)
    # ==========================================================

    async def extract_leads_rag_node(self, state: AgentState) -> Dict:
        """Uses Haiku 4.5 to structure raw text into JSON leads."""
        print("--- [NODE 3] EXTRACCIÓN RAG ---")
        raw_text = state.get("raw_search_text", "")
        profile_urls = state.get("profile_urls", [])

        if not raw_text:
            print("--- [RAG] Sin texto para procesar ---")
            return {"current_leads": []}

        # Call Haiku to structure the data
        leads = self._haiku_extract(raw_text)

        # Merge profile URLs into leads
        for i, lead in enumerate(leads):
            if i < len(profile_urls) and profile_urls[i]:
                lead["perfil_url"] = profile_urls[i]
            elif "perfil_url" not in lead:
                lead["perfil_url"] = ""

        return {"current_leads": leads}

    # ==========================================================
    #  NODE 4: CLASIFICACIÓN (Python puro — $0)
    # ==========================================================

    async def classify_leads_node(self, state: AgentState) -> Dict:
        """Classifies leads as ENTERPRISE / STARTER / SKIP using Python rules."""
        print("--- [NODE 4] CLASIFICACIÓN ---")
        leads = state.get("current_leads", [])
        classified = []

        for lead in leads:
            cargo = (lead.get("cargo") or "").lower()
            empresa = (lead.get("empresa") or "").lower()
            ubicacion = (lead.get("ubicacion") or "").lower()

            tier = "STARTER"  # Default

            # Check SKIP first
            if any(kw in cargo for kw in SKIP_KEYWORDS):
                tier = "SKIP"
            # Check ENTERPRISE
            elif (
                any(kw in cargo for kw in ENTERPRISE_KEYWORDS["cargos"])
                or any(kw in empresa for kw in ENTERPRISE_KEYWORDS["industrias"])
                or any(kw in ubicacion for kw in ENTERPRISE_KEYWORDS["ubicaciones"])
            ):
                tier = "ENTERPRISE"
            # Check STARTER
            elif (
                any(kw in cargo for kw in STARTER_KEYWORDS["cargos"])
                or any(kw in empresa for kw in STARTER_KEYWORDS["industrias"])
                or any(kw in ubicacion for kw in STARTER_KEYWORDS["ubicaciones"])
            ):
                tier = "STARTER"

            lead["tier"] = tier
            classified.append(lead)

            tier_emoji = {"ENTERPRISE": "🏢", "STARTER": "🚀", "SKIP": "⏭️"}
            print(f"   {tier_emoji.get(tier, '❓')} {lead.get('nombre', '?')} → {tier}")

        return {"classified_leads": classified}

    # ==========================================================
    #  NODE 5: GUARDAR EN DB (SQLite, sin duplicados)
    # ==========================================================

    async def save_leads_node(self, state: AgentState) -> Dict:
        """Saves classified leads to the database."""
        print("--- [NODE 5] PERSISTENCIA ---")
        leads = state.get("classified_leads", [])
        query = state.get("last_order_raw", "")

        if not leads:
            return {
                "messages": [("ai", "⚠️ No se encontraron leads para guardar.")],
                "db_report": "0 guardados",
            }

        # Save to DB
        report = self.lead_repo.save_leads(leads, query_origen=query)

        # Build summary message
        enterprise = [l for l in leads if l.get("tier") == "ENTERPRISE"]
        starter = [l for l in leads if l.get("tier") == "STARTER"]
        skipped = [l for l in leads if l.get("tier") == "SKIP"]

        summary_parts = [f"✅ Búsqueda completada: '{query}'\n"]

        if enterprise:
            summary_parts.append("🏢 **ENTERPRISE:**")
            for l in enterprise:
                summary_parts.append(
                    f"  • {l.get('nombre', '?')} | {l.get('cargo', '?')} en {l.get('empresa', '?')}"
                )

        if starter:
            summary_parts.append("\n🚀 **STARTER:**")
            for l in starter:
                summary_parts.append(
                    f"  • {l.get('nombre', '?')} | {l.get('cargo', '?')} en {l.get('empresa', '?')}"
                )

        if skipped:
            summary_parts.append(f"\n⏭️ Descartados: {len(skipped)}")

        summary_parts.append(
            f"\n💾 DB: {report['saved']} nuevos, "
            f"{report['duplicated']} duplicados, "
            f"{report['skipped']} omitidos"
        )

        ai_message = "\n".join(summary_parts)
        print(f"--- [NODE 5] {report} ---")

        return {
            "messages": [("ai", ai_message)],
            "db_report": str(report),
            "current_leads": leads,
        }


    # ==========================================================
    #  NODE 6: GENERAR MENSAJES PERSONALIZADOS (Sonnet 4)
    # ==========================================================

    async def generate_messages_node(self, state: AgentState) -> Dict:
        """Generates personalized LinkedIn connection messages per lead."""
        print("--- [NODE 6] GENERACIÓN DE MENSAJES ---")
        leads = state.get("classified_leads", [])

        # Only generate for ENTERPRISE and STARTER (skip SKIP)
        actionable_leads = [l for l in leads if l.get("tier") != "SKIP"]

        if not actionable_leads:
            return {
                "messages": [("ai", "⚠️ No hay leads calificados para generar mensajes.")],
                "generated_messages": [],
            }

        # Limit to top 3 leads to save tokens (user requested 2-3 tests)
        top_leads = actionable_leads[:3]
        generated = []

        for lead in top_leads:
            prompt = COLD_EMAIL_PROMPT.format(
                nombre=lead.get("nombre", "Profesional"),
                cargo=lead.get("cargo", "Decisor"),
                empresa=lead.get("empresa", "su empresa"),
                ubicacion=lead.get("ubicacion", ""),
                tier=lead.get("tier", "STARTER"),
            )

            message = await self._safe_sonnet_invoke(prompt)

            if message:
                lead["mensaje_generado"] = message
                generated.append({
                    "nombre": lead.get("nombre"),
                    "tier": lead.get("tier"),
                    "mensaje": message,
                })
                print(f"   ✉️ {lead.get('nombre')}: {message[:60]}...")
            else:
                lead["mensaje_generado"] = ""
                print(f"   ⚠️ {lead.get('nombre')}: No se pudo generar mensaje")

        # Build WhatsApp summary
        summary_parts = [f"✉️ Mensajes generados para {len(generated)} leads:\n"]
        for g in generated:
            tier_emoji = "🏢" if g["tier"] == "ENTERPRISE" else "🚀"
            summary_parts.append(f"{tier_emoji} **{g['nombre']}:**")
            summary_parts.append(f"  \"{g['mensaje']}\"\n")

        return {
            "messages": [("ai", "\n".join(summary_parts))],
            "generated_messages": generated,
        }


    # ==========================================================
    #  NODE 7: VISITAR Y CONECTAR (Playwright + Stealth)
    # ==========================================================

    async def visit_and_connect_node(self, state: AgentState) -> Dict:
        """Navigates to each profile, extracts more info, and prepares connection."""
        print("--- [NODE 7] ACCIÓN: VISITAR + CONECTAR ---")
        leads = state.get("classified_leads", [])
        
        # Actionable = Enterprise or Starter
        actionable = [l for l in leads if l.get("tier") != "SKIP"]
        if not actionable:
            return {"messages": [("ai", "⏭️ Sin leads para conectar.")]}

        # Initialize fresh browser
        browser = BrowserService()
        await browser.start(headless=False) # Visual monitoring for debug

        results = []
        # LIMIT: Only 3 leads per run to avoid bans
        for lead in actionable[:3]:
            try:
                url = lead.get("perfil_url")
                msg = lead.get("mensaje_generado", "")
                
                # HUMAN DELAY: 30-60 seconds between profiles
                wait_time = random.randint(30, 60)
                print(f"--- [BROWSER] Esperando {wait_time}s para sig. perfil... ---")
                await asyncio.sleep(wait_time)

                res = await browser.visit_profile_and_connect(url, msg)
                
                status_emoji = {"success": "✅", "skipped": "⏭️", "error": "❌"}
                print(f"   {status_emoji.get(res['status'], '❓')} {lead.get('nombre')}: {res['status']}")
                
                results.append(f"{status_emoji.get(res['status'], '❓')} {lead.get('nombre')}: {res['status']}")
                
                # If we got info, update the lead dict (investigation)
                if res.get("info"):
                    lead["investigacion_perfil"] = res["info"]

            except Exception as e:
                print(f"--- [BROWSER] Fallo en perfil {lead.get('nombre')}: {e}")

        await browser.close()
        
        summary = "\n".join(results)
        return {
            "messages": [("ai", f"🚀 **Acciones completadas:**\n{summary}")],
            "action_reports": results
        }


# Singleton instance
marketing_nodes = MarketingNodes()

