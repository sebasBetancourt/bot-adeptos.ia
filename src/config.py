import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask configuration
    FLASK_APP = os.getenv("FLASK_APP", "src/app.py")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    PORT = int(os.getenv("PORT", 5000))

    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

    # AI Configuration (Anthropic)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # LinkedIn Credentials (auto-login)
    LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///marketing_db.sqlite") # Default to SQLite for easy initial startup

    # LangGraph Configuration
    # Add any specific graph settings here
