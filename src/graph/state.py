from typing import Annotated, TypedDict, List, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    Complete state for the AI Marketing Agent workflow.
    Passed between all 6 nodes in the graph.
    """
    # LangGraph messages
    messages: Annotated[List[BaseMessage], add_messages]

    # Routing Context
    intention: str                  # e.g., "REQUEST_REPORT" or "MARKETING_LEAD"
    source_channel: str             # e.g., "whatsapp" or "teams"
    is_admin: bool                  # True if sender is Admin (Jefe)

    # Contact context
    whatsapp_user: str              # Sender phone number

    # Search context
    last_order_raw: str             # Original user message / extracted query

    # Extraction pipeline
    raw_search_text: str            # Raw text from LinkedIn (NOT html)
    profile_urls: List[str]         # Profile URLs extracted from href attrs

    # Lead processing
    current_leads: List[dict]       # Leads structured by RAG
    classified_leads: List[dict]    # Leads with tier assigned

    # Personalized outreach (Node 6)
    generated_messages: List[dict]  # Cold outreach messages per lead

    # Output
    screenshot_path: str            # Path to screenshot
    db_report: str                  # "3 saved, 1 duplicate"
    is_approved: bool               # Approval status for sales action

