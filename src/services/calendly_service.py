"""
Calendly Service — OOP wrapper for the Calendly API v2.
Handles dynamic active event fetching.
"""
import requests
from typing import Optional
from src.core.config import Config

class CalendlyService:
    BASE_URL = "https://api.calendly.com"
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {Config.CALENDLY_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
    def _get_user_uri(self) -> Optional[str]:
        """Fetches the authenticated user's URI."""
        if not Config.CALENDLY_ACCESS_TOKEN:
            return None
            
        url = f"{self.BASE_URL}/users/me"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("resource", {}).get("uri")
            else:
                print(f"--- [CALENDLY] Error obteniendo URI del usuario: {response.text}")
                return None
        except Exception as e:
            print(f"--- [CALENDLY] Excepción al obtener usuario: {e}")
            return None

    def get_active_event_url(self) -> str:
        """
        Retrieves the scheduling url of the first active event type available for the user.
        Fallback to a generic message if API access fails.
        """
        if not Config.CALENDLY_ACCESS_TOKEN:
             return "(Link no disponible. Por favor, asegúrate de configurar CALENDLY_ACCESS_TOKEN)"

        user_uri = self._get_user_uri()
        if not user_uri:
            return "(Link no disponible. Revisa tus credenciales de Calendly)"
            
        url = f"{self.BASE_URL}/event_types"
        params = {"user": user_uri}  # Need to query event_types specifying the user
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                # Encontrar el primer evento ACTIVO
                events = data.get("collection", [])
                for evt in events:
                    if evt.get("active") and evt.get("scheduling_url"):
                        print(f"--- [CALENDLY] Evento Activo detectado: {evt.get('name')} ---")
                        return evt.get("scheduling_url")
                        
                print("--- [CALENDLY] No se encontraron eventos activos en la cuenta. ---")
                return "https://calendly.com (Aviso: Activa al menos un tipo de evento en tu cuenta)"
            else:
                print(f"--- [CALENDLY] Error obteniendo eventos: {response.text}")
                return "(Link temporalmente inaccesible)"
        except Exception as e:
            print(f"--- [CALENDLY] Excepción la obtener eventos: {e}")
            return "(Error interno de Calendly)"
