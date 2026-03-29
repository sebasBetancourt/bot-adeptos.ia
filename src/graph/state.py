from typing import Annotated, TypedDict, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Standard LangGraph message history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Custom business state
    whatsapp_user: str          # sender phone number
    last_order_raw: str         # The original user message/order
    current_leads: List[dict]   # Leads found in this session
    screenshot_path: str        # Path to the screenshot for approval
    is_approved: bool           # Approval status for sales action
