import msal
import requests
from datetime import datetime, timedelta
from src.core.config import Config
from src.core.database import db_manager
from src.domain.models import MicrosoftAuth

class MicrosoftGraphService:
    """Service to handle Microsoft Graph API operations (Teams, Planner, Calendar)."""
    
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        self.scopes = ["User.Read", "Tasks.ReadWrite", "OnlineMeetings.ReadWrite", "Calendars.ReadWrite"]
        self.authority = f"https://login.microsoftonline.com/{Config.MS_TENANT_ID}"
        self.client_id = Config.MS_CLIENT_ID
        self.client_secret = Config.MS_CLIENT_SECRET

    def _get_msal_app(self):
        return msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
        )

    def get_token(self):
        """Retrieves a valid access token from DB or refreshes it if needed."""
        db = next(db_manager.get_session())
        try:
            auth_entry = db.query(MicrosoftAuth).filter_by(phone_number=self.phone_number).first()
            if not auth_entry:
                return None

            # Check if token is expired (with 30s buffer)
            if auth_entry.expires_at > datetime.now() + timedelta(seconds=30):
                return auth_entry.access_token

            # Token expired, refresh it
            app = self._get_msal_app()
            result = app.acquire_token_by_refresh_token(
                auth_entry.refresh_token,
                scopes=self.scopes
            )

            if "access_token" in result:
                auth_entry.access_token = result["access_token"]
                if "refresh_token" in result:
                    auth_entry.refresh_token = result["refresh_token"]
                auth_entry.expires_at = datetime.now() + timedelta(seconds=result["expires_in"])
                db.commit()
                return auth_entry.access_token
            else:
                print(f"--- [MS-GRAPH] Error refreshing token: {result.get('error_description')} ---")
                return None
        finally:
            db.close()

    def create_meeting(self, subject: str, start_time: datetime, duration_minutes: int = 30):
        """Creates an Online Meeting in Teams and returns the join URL."""
        token = self.get_token()
        if not token:
            return None

        end_time = start_time + timedelta(minutes=duration_minutes)
        
        url = "https://graph.microsoft.com/v1.0/me/onlineMeetings"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "startDateTime": start_time.isoformat() + "Z",
            "endDateTime": end_time.isoformat() + "Z",
            "subject": subject,
            "lobbyBypassSettings": {
                "scope": "everyone"
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            data = response.json()
            return data.get("joinWebUrl")
        else:
            print(f"--- [MS-GRAPH] Error creating meeting: {response.text} ---")
            return None

    def create_planner_task(self, title: str, plan_id: str = None, bucket_id: str = None):
        """Creates a task in Microsoft Planner or ToDo."""
        token = self.get_token()
        if not token:
            return None

        # Fallback to config IDs if not provided
        plan_id = plan_id or Config.MS_PLAN_ID
        bucket_id = bucket_id or Config.MS_BUCKET_ID

        if not plan_id or not bucket_id:
            print("--- [MS-GRAPH] Plan ID or Bucket ID missing ---")
            return None

        url = "https://graph.microsoft.com/v1.0/planner/tasks"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "planId": plan_id,
            "bucketId": bucket_id,
            "title": title
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            return response.json().get("id")
        else:
            print(f"--- [MS-GRAPH] Error creating task: {response.text} ---")
            return None
