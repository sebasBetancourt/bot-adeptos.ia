from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import marketing_nodes

class MarketingWorkflow:
    """
    Handles the construction and compilation of the Agent's LangGraph workflow.
    Adheres to OOP principles.
    """
    def __init__(self):
        self.workflow = StateGraph(AgentState)
        self._build_graph()

    def _build_graph(self):
        # Define nodes from the instantiated nodes class
        self.workflow.add_node("receive_order", marketing_nodes.receive_order_node)
        self.workflow.add_node("navigate_browser", marketing_nodes.navigate_playwright_node)

        # Define edges (sequential flow for Phase 1)
        self.workflow.set_entry_point("receive_order")
        self.workflow.add_edge("receive_order", "navigate_browser")
        self.workflow.add_edge("navigate_browser", END)

    def compile(self):
        """Compiles the graph for execution."""
        return self.workflow.compile()

# Singleton instance of the compiled workflow
app_workflow = MarketingWorkflow().compile()
