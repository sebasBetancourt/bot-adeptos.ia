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
import os
from src.core.config import Config
from .state import AgentState
from src.services.browser_service import BrowserService
from src.repositories.lead_repository import LeadRepository
from src.services.targeting_service import TargetingService
from src.services.calendly_service import CalendlyService
from src.services.microsoft_service import MicrosoftGraphService

ENTERPRISE_KEYWORDS = TargetingService.get_enterprise_keywords()
STARTER_KEYWORDS = TargetingService.get_starter_keywords()
SKIP_KEYWORDS = TargetingService.get_skip_keywords()


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


def _load_context_and_skills() -> str:
    """Loads product context and marketing skills dynamically."""
    # Base directory relative to this file (src/graph/nodes.py -> root)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    context_text = ""
    skills_text = ""
    
    # Load Adeptos Context
    context_path = os.path.join(base_dir, ".agents", "product-marketing-context.md")
    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            context_text = f.read()
            
    # Load Skills
    skills_dir = os.path.join(base_dir, ".agents", "skills")
    if os.path.exists(skills_dir):
        for filename in ["cold-email.md", "sales-enablement.md"]:
            filepath = os.path.join(skills_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    skills_text += f"\n\n--- SKILL: {filename} ---\n{f.read()}"
                    
    return f"--- ACEPTOS PRODUCT CONTEXT ---\n{context_text}\n\n--- MARKETING SKILLS ---\n{skills_text}"

# ============================================================
#  COLD EMAIL PROMPT — Personalized outreach per lead
#  Based on dynamic context and Corey Haines skills
# ============================================================

COLD_EMAIL_PROMPT = """You are an expert cold outreach writer for Adeptos.

Write a SHORT LinkedIn connection message (max 300 chars) for this lead:
- Name: {nombre}
- Title: {cargo}
- Company: {empresa}
- Location: {ubicacion}
- Tier: {tier}

{system_context}

RULES:
1. Base the message strictly on the Product Context and Marketing Skills provided above.
2. Open with a personalized hook (observation about their role/company).
3. Frame the message around the problem/revenue leak, not just the product. Use case studies as proof.
4. Keep it conversational, peer-to-peer. NO "I hope this finds you well".
5. Keep it strictly under 300 characters (LinkedIn limit).
6. If location contains Colombia/Bogotá/Medellín → write in SPANISH
7. If location contains USA/Miami/NY → write in ENGLISH

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
    #  NODE: ENRUTADOR DE INTENCIÓN (Asistente Total)
    # ==========================================================

    async def intention_router_node(self, state: AgentState) -> Dict:
        """Determines if message is a REPORT request, VIRTUAL_ASSISTANT, or MARKETING search."""
        print("--- [NODE 0] ENRUTADOR DE INTENCIÓN ---")
        user_msg = state.get("last_order_raw", "")
        source = state.get("source_channel", "whatsapp")
        
        prompt = (
            f"Eres el Asistente Total de Adeptos (SalesOps). Tienes 6 funciones principales.\n"
            f"1. REQUEST_REPORT: El usuario pide métricas, datos, reportes o resumen de su base de datos/leads.\n"
            f"2. MARKET_INTELLIGENCE: El usuario pide 'analizar', 'investigar' o evaluar competencia.\n"
            f"3. MARKETING_LEAD: El usuario pide prospectar explícitamente leads de internet en LinkedIn.\n"
            f"4. VIRTUAL_ASSISTANT: El usuario saluda, hace preguntas generales o conversacionales.\n"
            f"5. SCHEDULE_TEAMS: El usuario (Jefe) pide explícitamente agendar una reunión o crear un enlace de Teams.\n"
            f"6. CREATE_TASK: El usuario (Jefe) pide agregar algo al backlog, a sus pendientes o crear una tarea.\n\n"
            f"Clasifica este mensaje basándote en su intención principal: '{user_msg}'\n"
            f"Responde SOLO, estrictamente, con una de las seis opciones. Si tienes duda o es un saludo, responde VIRTUAL_ASSISTANT."
        )

        response = await self._safe_sonnet_invoke(prompt)
        response_clean = response.strip() if response else ""
        valid_intentions = ["REQUEST_REPORT", "VIRTUAL_ASSISTANT", "MARKET_INTELLIGENCE", "MARKETING_LEAD", "SCHEDULE_TEAMS", "CREATE_TASK"]
        intention = response_clean if response_clean in valid_intentions else "VIRTUAL_ASSISTANT"
        
        # Bloqueo de Seguridad (RBAC): Sólo Administrador puede correr Scraper o Microsoft Tools
        is_admin = state.get("is_admin", False)
        if intention in ["MARKETING_LEAD", "SCHEDULE_TEAMS", "CREATE_TASK"] and not is_admin:
            print(f"--- [SECURITY] Usuario bloqueado de usar {intention} ---")
            intention = "VIRTUAL_ASSISTANT"

        print(f"--- [ROUTER] Intención detectada: {intention} desde {source} ---")
        return {"intention": intention}

    # ==========================================================
    #  NODE: MARKET INTELLIGENCE (Tavily AI Web Scraper)
    # ==========================================================
    
    async def market_intelligence_node(self, state: AgentState) -> Dict:
        """Uses Tavily REST API to search competitor metrics and SWOT."""
        print("--- [NODE] MARKET INTELLIGENCE ---")
        query = state.get("last_order_raw", "")
        
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=Config.TAVILY_API_KEY)
            
            # Scrapeo profundo (Búsqueda API 0 tokens)
            print(f"Buscando en tiempo real: {query}")
            response = tavily.search(query=query, search_depth="basic", max_results=3)
            results = "\n\n".join([r.get("content", "") for r in response.get("results", [])])
            
            # Consumo de LLM formativo
            prompt = (
                f"Actúa como un Director de Inteligencia de Mercado B2B.\n"
                f"El usuario (tu jefe de ventas) pide: '{query}'.\n\n"
                f"Aquí tienes Data Fresca Scrapeada de la web de Tavily:\n{results}\n\n"
                f"Cruza esta información y redacta un Breve Cuadro Comparativo (usando Markdown) "
                f"destacando fortalezas, debilidades o insights críticos del mercado objetivo / competencia.\n"
            )
            
            analysis = await self._safe_sonnet_invoke(prompt)
            if not analysis:
                analysis = "⚠️ Error: No se pudo formatear el reporte web de Tavily en Sonnet."
            
            return {"messages": [("ai", analysis)]}
            
        except ImportError:
            return {"messages": [("ai", "⚠️ Falla crítica: librería 'tavily-python' no instalada en la imagen de Docker.")]}
        except Exception as e:
            return {"messages": [("ai", f"⚠️ Hubo un error procesando la inteligencia de mercado: {e}")]}

    # ==========================================================
    #  NODE: GENERAR REPORTE (Dashboard SQL)
    # ==========================================================

    async def generate_report_node(self, state: AgentState) -> Dict:
        """Fetches advanced DB stats and generates SalesOps dashboard mapping revenue leaks."""
        print("--- [NODE] GENERAR REPORTE (Dashboard) ---")
        
        from src.core.database import db_manager
        from src.domain.models import Lead, Meeting, LeadStatus
        from sqlalchemy import func
        
        db = next(db_manager.get_session())
        
        try:
            total_leads = db.query(func.count(Lead.id)).scalar() or 0
            calificados = db.query(func.count(Lead.id)).filter(Lead.estado == LeadStatus.CALIFICADO).scalar() or 0
            
            total_meetings = db.query(func.count(Meeting.id)).scalar() or 0
            
            tasa = 0.0
            if total_leads > 0:
                tasa = (total_meetings / total_leads) * 100
                
            enterprise_count = db.query(func.count(Lead.id)).filter(Lead.tier == "ENTERPRISE").scalar() or 0
            revenue_leak = enterprise_count * 8500
            
            report_msg = (
                f"📊 *Dashboard SalesOps Adeptos*\n\n"
                f"Origen de la petición: {state.get('source_channel', 'whatsapp').capitalize()}\n\n"
                f"👥 *Pipeline de Leads:*\n"
                f"- Leads Totales: {total_leads}\n"
                f"- Leads Calificados: {calificados}\n\n"
                f"📅 *Agendamiento y Conversión:*\n"
                f"- Reuniones Cerradas (Meetings): {total_meetings}\n"
                f"- Tasa de Conversión General: {tasa:.2f}%\n\n"
                f"💸 *Fuga de Ingresos Total (Revenue Leak):*\n"
                f"Bajo nuestro audit de industria, si no atiendes instantáneamente a tus {enterprise_count} leads Enterprise, "
                f"tienes un Revenue Leak (fuga) acumulado de *${revenue_leak:,.2f}/mes*.\n\n"
                f"Apto para próxima instrucción."
            )
            return {"messages": [("ai", report_msg)]}
        except Exception as e:
            return {"messages": [("ai", f"⚠️ Hubo un error procesando el Pipeline Dashboard: {e}")]}
        finally:
            db.close()

    # ==========================================================
    #  NODE: ASISTENTE VIRTUAL (General & Agenda)
    # ==========================================================

    async def virtual_assistant_node(self, state: AgentState) -> Dict:
        """Handles general conversation, greetings, and scheduling using Claude Skills."""
        print("--- [NODE] ASISTENTE VIRTUAL ---")
        
        messages = state.get("messages", [])
        
        # Extract Calendly link and skills context for scheduling
        calendly = CalendlyService()
        meeting_url = calendly.get_active_event_url()
        system_context = _load_context_and_skills()
        
        # Build prompt history
        history_text = ""
        current_msg = ""
        if messages:
             for m in messages[:-1]:
                 if isinstance(m, tuple):
                     history_text += f"{m[0].upper()}: {m[1]}\n"
                 else:
                     history_text += f"{m.type.upper()}: {m.content}\n"
             
             last_m = messages[-1]
             current_msg = last_m[1] if isinstance(last_m, tuple) else last_m.content

        is_admin = state.get("is_admin", False)

        if is_admin:
            prompt = (
                f"Eres el Jefe de Operaciones corporativo de Adeptos.\n"
                f"El usuario con el que estás hablando AHORA MISMO es TU JEFE DIRECTO (Administrador/Sebas).\n"
                f"Tu rol primario es ejecutar comandos, manejar agenda internamente, dar estatus de las operaciones "
                f"y asistir de forma directa, técnica y eficiente. NO INTENTES VENDERLE NADA NI LE DES EL PITCH DE VENTAS.\n\n"
                f"Contexto (Skills):\n{system_context}\n\n"
                f"Historial de conversación reciente:\n{history_text}\n"
                f"Jefe dice: {current_msg}\n\n"
                f"Responde corto, al grano, técnico y con actitud resolutiva."
            )
        else:
            prompt = (
                f"Eres el Asistente Virtual Principal de Adeptos y tu primera funcón principal es la agenda.\n"
                f"Tu rol primario es organizar reuniones, agendar citas, organizar llamadas de Teams/Google Meet, "
                f"informar sobre reportes y asistir al usuario amablemente. "
                f"Tu rol secundario, si el usuario explícitamente lo solicita, es buscar leads en LinkedIn.\n\n"
                f"Contexto y Habilidades (Skills):\n{system_context}\n\n"
                f"Instrucciones Clave:\n"
                f"1. Si el usuario saluda o no es claro (ej. 'Hola'), SALÚDALO amablemente y PREGÚNTALE "
                f"qué desea hacer hoy: ¿Buscar leads?, ¿Agendar una cita/evento?, o ¿Solicitar reportes de reuniones?\n"
                f"2. Si el usuario quiere agendar, usa tus habilidades de ventas para persuadir sutilmente sobre el "
                f"problema de la fuga de ingresos ($8,500/mes) y entrega este único enlace de agendamiento: {meeting_url}\n\n"
                f"Historial de conversación reciente:\n{history_text}\n"
                f"Usuario ahora dice: {current_msg}\n\n"
                f"Responde de forma útil, conversacional y directa. NUNCA digas que eres una IA."
            )
        
        message = await self._safe_sonnet_invoke(prompt)
        
        if not message:
            message = "Disculpa, tuve un problema interno. ¿En qué te puedo ayudar hoy? (Buscar leads, agendar cita o ver reportes)"
            
        return {"messages": [("ai", message)]}

    # ==========================================================
    #  NODE: EJECUTOR MICROSOFT (Teams & Planner)
    # ==========================================================

    async def microsoft_executor_node(self, state: AgentState) -> Dict:
        """Executes actual API calls to Teams or Planner via MicrosoftGraphService."""
        print("--- [NODE] EJECUTOR MICROSOFT ---")
        is_admin = state.get("is_admin", False)
        phone = state.get("whatsapp_user", "")
        intention = state.get("intention", "")
        msg = state.get("last_order_raw", "")

        if not is_admin:
            return {"messages": [("ai", "Lo siento, estas funciones administrativas están reservadas solo para el Jefe de Operaciones.")]}

        ms_service = MicrosoftGraphService(phone)
        token = ms_service.get_token()

        if not token:
            # Generate Login Link
            # Note: We need a way to build the absolute URL here. Assuming we can get it from context or hardcode ngrok for now.
            login_url = f"{Config.MS_REDIRECT_URI.replace('/login/microsoft/callback', '/login/microsoft')}?phone={phone}"
            return {"messages": [("ai", f"⚠️ Jefe, aún no has vinculado tu cuenta de Microsoft. Por seguridad, haz clic aquí para autorizar al asistente:\n\n{login_url}")]}

        if intention == "SCHEDULE_TEAMS":
            # Extract date/time from message (simplistic extraction for now)
            # In a real scenario, use LLM to parse ISO format
            prompt = f"Extract a clean subject and a plausible ISO datetime (UTC) from this user request: '{msg}'. Respond ONLY with JSON like {{'subject': '...', 'start_time': '2026-04-01T15:00:00'}}. If no date, use tomorrow at 10am."
            data_raw = await self._safe_sonnet_invoke(prompt)
            try:
                import json
                info = json.loads(data_raw)
                dt = datetime.fromisoformat(info["start_time"])
                join_url = ms_service.create_meeting(info["subject"], dt)
                if join_url:
                    return {"messages": [("ai", f"✅ Listo Jefe. Reunión de Teams agendada: '{info['subject']}'\n\nLink de acceso:\n{join_url}")]}
            except:
                pass
            return {"messages": [("ai", "❌ No se pudo agendar la reunión. Verifica el formato de la fecha.")]}

        elif intention == "CREATE_TASK":
            # Extract task title
            prompt = f"Extract a concise task title for Planner from this request: '{msg}'. Respond ONLY with the title."
            task_title = await self._safe_sonnet_invoke(prompt)
            task_id = ms_service.create_planner_task(task_title or msg)
            if task_id:
                return {"messages": [("ai", f"✅ Tarea añadida a tu backlog de Planner: '{task_title}'")]}
            else:
                return {"messages": [("ai", "❌ Error al crear la tarea en Planner. ¿Configuraste el MS_PLAN_ID en el .env?")]}

        return {"messages": [("ai", "Intención de Microsoft no reconocida.")]}

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
                lead["linkedin_url"] = profile_urls[i]
            elif "linkedin_url" not in lead:
                lead["linkedin_url"] = ""

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
    #  NODE: MARKET INTELLIGENCE (Tavily AI)
    # ==========================================================

    async def market_intelligence_node(self, state: AgentState) -> Dict:
        """Uses Tavily Search API to research ENTERPRISE leads' companies."""
        print("--- [NODE] MARKET INTELLIGENCE (Tavily) ---")
        leads = state.get("classified_leads", [])
        
        # Only research ENTERPRISE leads to conserve free tier API calls
        enterprise_leads = [l for l in leads if l.get("tier") == "ENTERPRISE"]
        
        if not enterprise_leads:
            print("--- [TAVILY] No Enterprise leads to research. Skipping. ---")
            return {"classified_leads": leads}
            
        try:
            from tavily import TavilyClient
            if not Config.TAVILY_API_KEY:
                print("--- [TAVILY] No API Key found, skipping market intelligence. ---")
                return {"classified_leads": leads}
                
            tavily_client = TavilyClient(api_key=Config.TAVILY_API_KEY)
            
            for lead in enterprise_leads:
                empresa = lead.get("empresa")
                if not empresa or empresa in ["N/A", "Tu Empresa"]:
                    continue
                    
                print(f"--- [TAVILY] Buscando información sobre: {empresa} ---")
                try:
                    query = f"What is {empresa} company doing? What is their business model and recent news?"
                    response = tavily_client.search(query=query, search_depth="basic")
                    
                    # Extract insights from results
                    if "results" in response and response["results"]:
                        # Concatenate top 2 results as research
                        insights = "\n".join([f"- {res['content']}" for res in response["results"][:2]])
                        lead["company_research"] = insights
                        print(f"--- [TAVILY] Insights obtenidos para {empresa} ---")
                    else:
                        lead["company_research"] = ""
                        
                except Exception as e:
                    print(f"--- [TAVILY] Error buscando en Tavily: {e} ---")
                    lead["company_research"] = ""
                    
        except ImportError:
            print("--- [TAVILY] modulo 'tavily' no instalado. Usa: pip install tavily-python ---")
            
        # Update original list with the enriched enterprise leads
        for original_lead in leads:
            for e_lead in enterprise_leads:
                if original_lead.get("linkedin_url") == e_lead.get("linkedin_url"):
                    original_lead["company_research"] = e_lead.get("company_research", "")
                    
        return {"classified_leads": leads}

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
        pdf_generated_files = []

        # Load dynamic context and skills
        system_context = _load_context_and_skills()
        
        from src.services.report_service import ReportService
        report_svc = ReportService()

        for lead in top_leads:
            prompt = COLD_EMAIL_PROMPT.format(
                nombre=lead.get("nombre", "Profesional"),
                cargo=lead.get("cargo", "Decisor"),
                empresa=lead.get("empresa", "su empresa"),
                ubicacion=lead.get("ubicacion", ""),
                tier=lead.get("tier", "STARTER"),
                system_context=system_context,
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
                
                # --- VALUE-FIRST MARKETING: Generar PDF automático si es Enterprise ---
                if lead.get("tier") == "ENTERPRISE":
                    print(f"   📄 Generando Auditoría de Fuga Financiera PDF para {lead.get('empresa')}...")
                    pdf_path = report_svc.generate_revenue_leak_audit(lead)
                    pdf_generated_files.append((lead.get('empresa'), pdf_path))

            else:
                lead["mensaje_generado"] = ""
                print(f"   ⚠️ {lead.get('nombre')}: No se pudo generar mensaje")

        # Build WhatsApp summary
        summary_parts = [f"✉️ Mensajes Listos para {len(generated)} leads:\n"]
        for g in generated:
            tier_emoji = "🏢" if g["tier"] == "ENTERPRISE" else "🚀"
            summary_parts.append(f"{tier_emoji} **{g['nombre']}:**")
            summary_parts.append(f"  \"{g['mensaje']}\"\n")
            
        if pdf_generated_files:
            summary_parts.append(f"\n📑 *{len(pdf_generated_files)} Value-First Assets Generados (PDF)*:")
            for p in pdf_generated_files:
                summary_parts.append(f" - Auditoría: {p[0]} ({p[1]})")

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
                url = lead.get("linkedin_url", lead.get("perfil_url"))
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

