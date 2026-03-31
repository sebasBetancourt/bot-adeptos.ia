import asyncio
import msal
import requests
from flask import Blueprint, request, redirect
from datetime import datetime, timedelta
from src.core.config import Config
from src.core.database import db_manager
from src.domain.models import ChatHistory, AdminUser, MicrosoftAuth
from src.services.twilio_service import TwilioService
from src.graph.workflow import app_workflow

# Create Blueprint
webhook_bp = Blueprint('webhook_bp', __name__)

@webhook_bp.route("/", methods=["GET"])
def index():
    return "AI Marketing Co-Pilot (SAAM) is running on Clean Architecture with Postgres. 🚀"

# --- MICROSOFT OAUTH2 FLOW ---

def _get_msal_app():
    return msal.ConfidentialClientApplication(
        Config.MS_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{Config.MS_TENANT_ID}",
        client_credential=Config.MS_CLIENT_SECRET,
    )

@webhook_bp.route("/login/microsoft", methods=["GET"])
def microsoft_login():
    """Initiates Microsoft OAuth2 flow."""
    phone = request.args.get("phone") # Should come from the WhatsApp link
    if not phone:
        return "Error: Falta el número de teléfono en la petición.", 400
    
    app = _get_msal_app()
    auth_url = app.get_authorization_request_url(
        scopes=["User.Read", "Tasks.ReadWrite", "OnlineMeetings.ReadWrite", "Calendars.ReadWrite"],
        redirect_uri=Config.MS_REDIRECT_URI,
        state=phone # Pass the phone number to the callback
    )
    return redirect(auth_url)

@webhook_bp.route("/login/microsoft/callback", methods=["GET"])
def microsoft_callback():
    """Handles Microsoft OAuth2 callback and stores tokens."""
    code = request.args.get("code")
    phone = request.args.get("state") # The phone number we passed earlier
    
    if not code or not phone:
        return "Error: Falta el código o el estado (teléfono) en el callback.", 400

    app = _get_msal_app()
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read", "Tasks.ReadWrite", "OnlineMeetings.ReadWrite", "Calendars.ReadWrite"],
        redirect_uri=Config.MS_REDIRECT_URI
    )

    if "access_token" in result:
        db = next(db_manager.get_session())
        try:
            # Upsert logic for MicrosoftAuth
            auth_entry = db.query(MicrosoftAuth).filter_by(phone_number=phone).first()
            if not auth_entry:
                auth_entry = MicrosoftAuth(phone_number=phone)
                db.add(auth_entry)
            
            auth_entry.access_token = result["access_token"]
            auth_entry.refresh_token = result["refresh_token"]
            auth_entry.expires_at = datetime.now() + timedelta(seconds=result["expires_in"])
            auth_entry.scope = result.get("scope")
            auth_entry.tenant_id = Config.MS_TENANT_ID
            
            db.commit()
            
            # --- HELPER: Print Planner Info for Sebas to console ---
            try:
                p_url = "https://graph.microsoft.com/v1.0/me/planner/plans"
                p_headers = {"Authorization": f"Bearer {result['access_token']}"}
                p_res = requests.get(p_url, headers=p_headers).json()
                print("\n" + "="*50)
                print("📋 CONFIGURACIÓN DE PLANNER PARA SEBAS:")
                for plan in p_res.get('value', []):
                    print(f"Plan: {plan['title']} | ID: {plan['id']}")
                    # Get buckets for this plan
                    b_url = f"https://graph.microsoft.com/v1.0/planner/plans/{plan['id']}/buckets"
                    b_res = requests.get(b_url, headers=p_headers).json()
                    for bucket in b_res.get('value', []):
                        print(f"  --> Bucket: {bucket['name']} | ID: {bucket['id']}")
                print("="*50 + "\n")
            except:
                pass

            return f"<h1>✅ ¡Éxito!</h1><p>Cuenta de Microsoft vinculada correctamente al número {phone}. Ya puedes cerrar esta ventana.</p>"
        finally:
            db.close()
    else:
        return f"Error en la vinculación: {result.get('error_description')}", 500

@webhook_bp.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages from Twilio."""
    data = request.form
    incoming_msg = data.get("Body", "").strip()
    sender_phone = data.get("From", "")

    print(f"Mensaje recibido de {sender_phone}: {incoming_msg}")

    db = next(db_manager.get_session())
    try:
        # Check Admin Role
        admin_match = db.query(AdminUser).filter_by(phone_number=sender_phone).first()
        is_admin = admin_match is not None
        if is_admin:
            print(f"--- [AUTH] SENDER ({sender_phone}) ES ADMIN ---")

        # Fetch History from DB (last 20 messages for context)
        past_msgs_db = db.query(ChatHistory).filter_by(phone_number=sender_phone).order_by(ChatHistory.id.asc()).limit(20).all()
        # Convert DB history to LangGraph format
        message_history = []
        for p in past_msgs_db:
             message_history.append((p.role, p.content))
        
        # Save Incoming Message
        user_msg_db = ChatHistory(phone_number=sender_phone, role="user", content=incoming_msg)
        db.add(user_msg_db)
        db.commit()

        # Add the new message to the active array
        message_history.append(("user", incoming_msg))

        # Initial state for the pipeline
        initial_state = {
            "messages": message_history,
            "source_channel": "whatsapp",
            "is_admin": is_admin,
            "intention": "",
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
        result_state = asyncio.run(app_workflow.ainvoke(initial_state))

        # Get last AI message
        last_ai_msg = result_state["messages"][-1].content
        
        # Save Outgoing Message
        ai_msg_db = ChatHistory(phone_number=sender_phone, role="ai", content=last_ai_msg)
        db.add(ai_msg_db)
        db.commit()

        return TwilioService.send_simple_reply(last_ai_msg)

    except Exception as e:
        print(f"--- [ERROR] Pipeline falló: {e} ---")
        return TwilioService.send_simple_reply(
            "⚠️ Hubo un error procesando tu solicitud. Intenta de nuevo."
        )
    finally:
        db.close()
