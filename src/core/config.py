import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask configuration
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

    # Database Configuration - PostgreSQL
    # Default fallback to a generic dev postgres URL
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:contraseña@localhost:5432/adeptos_db")

    # Calendly API Integration
    CALENDLY_ACCESS_TOKEN = os.getenv("CALENDLY_ACCESS_TOKEN")
    
    # Tavily Web Search API
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    # Microsoft Graph API (Planner, Teams & Calendar)
    MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
    MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
    MS_TENANT_ID = os.getenv("MS_TENANT_ID", "common") # "common" for multitenant
    MS_REDIRECT_URI = os.getenv("MS_REDIRECT_URI", "https://localhost:5000/login/microsoft/callback")
    
    # Planner IDs (to be filled later)
    MS_PLAN_ID = os.getenv("MS_PLAN_ID")
    MS_BUCKET_ID = os.getenv("MS_BUCKET_ID")

