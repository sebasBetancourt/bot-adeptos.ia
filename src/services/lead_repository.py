"""
Lead Repository — CRUD for leads with duplicate prevention.
"""
from sqlalchemy.exc import IntegrityError
from src.database import SessionLocal
from src.models.lead import Lead, LeadStatus


class LeadRepository:
    """Handles all database operations for Leads."""

    def save_leads(self, leads: list[dict], query_origen: str = "") -> dict:
        """
        Saves a list of lead dicts to the database.
        Skips duplicates based on perfil_url.

        Returns: {"saved": int, "duplicated": int, "skipped": int}
        """
        db = SessionLocal()
        saved, duplicated, skipped = 0, 0, 0

        try:
            for lead_data in leads:
                tier = lead_data.get("tier", "STARTER")

                # Skip leads marked as SKIP
                if tier == "SKIP":
                    skipped += 1
                    continue

                perfil_url = lead_data.get("perfil_url", "")
                if not perfil_url:
                    skipped += 1
                    continue

                # Check for duplicate
                existing = db.query(Lead).filter(Lead.perfil_url == perfil_url).first()
                if existing:
                    duplicated += 1
                    continue

                # Create new lead
                new_lead = Lead(
                    nombre=lead_data.get("nombre", ""),
                    cargo=lead_data.get("cargo", ""),
                    empresa=lead_data.get("empresa", ""),
                    ubicacion=lead_data.get("ubicacion", ""),
                    industria=lead_data.get("industria", ""),
                    perfil_url=perfil_url,
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

    def get_all_leads(self, tier: str = None) -> list[dict]:
        """Returns all leads, optionally filtered by tier."""
        db = SessionLocal()
        try:
            query = db.query(Lead)
            if tier:
                query = query.filter(Lead.tier == tier)
            return [lead.to_dict() for lead in query.all()]
        finally:
            db.close()

    def count_leads(self) -> dict:
        """Returns lead counts by tier."""
        db = SessionLocal()
        try:
            total = db.query(Lead).count()
            enterprise = db.query(Lead).filter(Lead.tier == "ENTERPRISE").count()
            starter = db.query(Lead).filter(Lead.tier == "STARTER").count()
            return {"total": total, "enterprise": enterprise, "starter": starter}
        finally:
            db.close()
