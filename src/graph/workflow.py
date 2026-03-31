"""
Marketing Workflow — 7-node LangGraph pipeline.

Flow:
  1. receive_order       → Extract search query from WhatsApp
  2. navigate_browser    → Stealth LinkedIn search + text extraction
  3. extract_rag         → Claude structures text → JSON
  4. classify_leads      → Python rules assign tier ($0)
  5. generate_messages   → Personalized cold outreach per lead (Sonnet 4)
  6. save_leads          → SQLite persistence (no duplicates + stored message)
  7. visit_and_connect   → Node 7: Action (Navigate to profile, Connect, Scrap more)
"""
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import marketing_nodes


class MarketingWorkflow:
    """Builds and compiles the 7-node LangGraph workflow."""

    def __init__(self):
        self.workflow = StateGraph(AgentState)
        self._build_graph()

    def _build_graph(self):
        nodes = marketing_nodes

        # Register all nodes
        self.workflow.add_node("intention_router", nodes.intention_router_node)
        self.workflow.add_node("market_intelligence", nodes.market_intelligence_node)
        self.workflow.add_node("generate_report", nodes.generate_report_node)
        self.workflow.add_node("virtual_assistant", nodes.virtual_assistant_node)
        self.workflow.add_node("microsoft_executor", nodes.microsoft_executor_node)
        self.workflow.add_node("receive_order", nodes.receive_order_node)
        self.workflow.add_node("navigate_browser", nodes.navigate_playwright_node)
        self.workflow.add_node("extract_rag", nodes.extract_leads_rag_node)
        self.workflow.add_node("classify_leads", nodes.classify_leads_node)
        self.workflow.add_node("generate_messages", nodes.generate_messages_node)
        self.workflow.add_node("save_leads", nodes.save_leads_node)
        self.workflow.add_node("visit_and_connect", nodes.visit_and_connect_node)

        # Base entrypoint
        self.workflow.set_entry_point("intention_router")

        # Routing conditional logic
        def route_intention(state):
            return state.get("intention", "VIRTUAL_ASSISTANT")
            
        self.workflow.add_conditional_edges(
            "intention_router",
            route_intention,
            {
                "REQUEST_REPORT": "generate_report",
                "MARKET_INTELLIGENCE": "market_intelligence",
                "VIRTUAL_ASSISTANT": "virtual_assistant",
                "SCHEDULE_TEAMS": "microsoft_executor",
                "CREATE_TASK": "microsoft_executor",
                "MARKETING_LEAD": "receive_order"
            }
        )

        # Assitant standalone flows ending immediately
        self.workflow.add_edge("generate_report", END)
        self.workflow.add_edge("market_intelligence", END)
        self.workflow.add_edge("virtual_assistant", END)
        self.workflow.add_edge("microsoft_executor", END)

        # Standard Marketing Flow
        self.workflow.add_edge("receive_order", "navigate_browser")
        self.workflow.add_edge("navigate_browser", "extract_rag")
        self.workflow.add_edge("extract_rag", "classify_leads")
        self.workflow.add_edge("classify_leads", "market_intelligence")
        self.workflow.add_edge("market_intelligence", "generate_messages")
        self.workflow.add_edge("generate_messages", "save_leads")
        self.workflow.add_edge("save_leads", "visit_and_connect")
        self.workflow.add_edge("visit_and_connect", END)

    def compile(self):
        """Compiles the graph for execution."""
        return self.workflow.compile()


# Singleton compiled workflow
app_workflow = MarketingWorkflow().compile()
