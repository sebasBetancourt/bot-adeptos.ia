import asyncio
from flask import Flask, request
from src.services.twilio_service import TwilioService
from src.graph.workflow import app_workflow
from src.config import Config
import os

app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
    return "AI Marketing Co-Pilot is running."

@app.route("/whatsapp", methods=['POST'])
def whatsapp_webhook():
    """
    Handle incoming WhatsApp messages from Twilio.
    """
    # 1. Parse incoming data
    data = request.form
    incoming_msg = data.get('Body', '').strip()
    sender_phone = data.get('From', '')

    print(f"Mensaje recibido de {sender_phone}: {incoming_msg}")

    # 2. Prepare state for LangGraph
    initial_state = {
        "messages": [("user", incoming_msg)],
        "whatsapp_user": sender_phone,
        "last_order_raw": incoming_msg,
        "current_leads": [],
        "screenshot_path": "",
        "is_approved": False
    }

    # 3. Run the workflow
    # Note: For MVP Phase 1, we run it synchronously here. 
    # In production, we'd offload to a background worker (Celery/Redis).
    result_state = asyncio.run(app_workflow.ainvoke(initial_state))

    # 4. Get the last AI response
    last_ai_msg = result_state["messages"][-1].content

    # 5. Build Twilio Response
    # If the workflow produced a screenshot, we might want to send it
    if result_state.get("screenshot_path"):
        # For now, we just reply with text and mention the screenshot
        # In Phase 2, we would host the screenshot and send the URL
        return TwilioService.send_simple_reply(f"{last_ai_msg}\n\n[Captura generada y pendiente de aprobación]")
    
    return TwilioService.send_simple_reply(last_ai_msg)

from src.database import init_db

if __name__ == "__main__":
    init_db()
    app.run(port=Config.PORT, debug=True)
