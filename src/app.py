"""
AI Marketing Co-Pilot — Flask Entry Point.
Receives WhatsApp messages via Twilio webhook and
triggers the 5-node LangGraph pipeline.
"""
import asyncio
from flask import Flask, request
from src.services.twilio_service import TwilioService
from src.graph.workflow import app_workflow
from src.config import Config

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return "AI Marketing Co-Pilot (SAAM) is running. 🚀"


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages from Twilio."""
    data = request.form
    incoming_msg = data.get("Body", "").strip()
    sender_phone = data.get("From", "")

    print(f"Mensaje recibido de {sender_phone}: {incoming_msg}")

    # Initial state for the 6-node pipeline
    initial_state = {
        "messages": [("user", incoming_msg)],
        "whatsapp_user": sender_phone,
        "last_order_raw": incoming_msg,
        "raw_search_text": "",
        "profile_urls": [],
        "current_leads": [],
        "classified_leads": [],
        "generated_messages": [],
        "screenshot_path": "",
        "db_report": "",
        "is_approved": False,
    }

    # Run the full pipeline
    try:
        result_state = asyncio.run(app_workflow.ainvoke(initial_state))

        # Get last AI message
        last_ai_msg = result_state["messages"][-1].content
        return TwilioService.send_simple_reply(last_ai_msg)

    except Exception as e:
        print(f"--- [ERROR] Pipeline falló: {e} ---")
        return TwilioService.send_simple_reply(
            "⚠️ Hubo un error procesando tu solicitud. Intenta de nuevo."
        )


from src.database import init_db

if __name__ == "__main__":
    init_db()
    print("🚀 SAAM Bot iniciado — esperando órdenes por WhatsApp...")
    app.run(port=Config.PORT, debug=True)
