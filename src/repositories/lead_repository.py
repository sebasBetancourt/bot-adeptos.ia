"""
Lead Repository — Data access for leads integrating abstract OOP principles.
"""
from typing import Dict, List, Any
from sqlalchemy.exc import IntegrityError
from src.domain.models import Lead, LeadStatus
from src.repositories.base_repository import BaseRepository

class LeadRepository(BaseRepository[Lead]):
    """Handles all database operations for Leads."""

    def __init__(self):
        super().__init__(Lead)

    def save_leads(self, leads: List[Dict[str, Any]], query_origen: str = "") -> Dict[str, int]:
        """
        Saves a list of lead dicts to the database.
        Skips duplicates based on perfil_url.

        Returns: {"saved": int, "duplicated": int, "skipped": int}
        """
        db = self.get_session()
        saved, duplicated, skipped = 0, 0, 0

        try:
            for lead_data in leads:
                tier = lead_data.get("tier", "STARTER")

                # Skip leads marked as SKIP
                if tier == "SKIP":
                    skipped += 1
                    continue

                linkedin_url = lead_data.get("linkedin_url", lead_data.get("perfil_url", ""))
                if not linkedin_url:
                    skipped += 1
                    continue

                # Check for duplicate
                existing = db.query(self.model).filter(self.model.linkedin_url == linkedin_url).first()
                if existing:
                    duplicated += 1
                    continue

                # Create new lead
                new_lead = self.model(
                    nombre=lead_data.get("nombre", ""),
                    cargo=lead_data.get("cargo", ""),
                    empresa=lead_data.get("empresa", ""),
                    ubicacion=lead_data.get("ubicacion", ""),
                    industria=lead_data.get("industria", ""),
                    linkedin_url=linkedin_url,
                    lead_score=lead_data.get("lead_score", 0),
                    tier=tier,
                    query_origen=query_origen,
                    ultimo_mensaje=lead_data.get("mensaje_generado", ""),
                    estado=LeadStatus.CALIFICADO if tier != "SKIP" else LeadStatus.DESCARTADO,
                )
                db.add(new_lead)
                saved += 1

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"--- [DB] Error guardando leads: {e} ---")
        finally:
            db.close()

        return {"saved": saved, "duplicated": duplicated, "skipped": skipped}

    def get_by_tier(self, tier: str = None) -> List[Dict[str, Any]]:
        """Returns all leads, optionally filtered by tier as dicts."""
        db = self.get_session()
        try:
            query = db.query(self.model)
            if tier:
                query = query.filter(self.model.tier == tier)
            return [lead.to_dict() for lead in query.all()]
        finally:
            db.close()

    def count_leads(self) -> Dict[str, int]:
        """Returns lead counts by tier."""
        db = self.get_session()
        try:
            total = db.query(self.model).count()
            enterprise = db.query(self.model).filter(self.model.tier == "ENTERPRISE").count()
            starter = db.query(self.model).filter(self.model.tier == "STARTER").count()
            return {"total": total, "enterprise": enterprise, "starter": starter}
        finally:
            db.close()
