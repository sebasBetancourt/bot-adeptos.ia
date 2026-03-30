import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, func
from src.database import Base


class LeadStatus(enum.Enum):
    NUEVO = "NUEVO"
    CALIFICADO = "CALIFICADO"
    DESCARTADO = "DESCARTADO"
    PENDIENTE_MENSAJE = "PENDIENTE_MENSAJE"
    CONTACTADO = "CONTACTADO"
    RESPONDIO = "RESPONDIO"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    # --- Datos del Perfil ---
    nombre = Column(String(255), nullable=True)
    cargo = Column(String(255), nullable=True)
    empresa = Column(String(255), nullable=True)
    ubicacion = Column(String(255), nullable=True)
    industria = Column(String(255), nullable=True)

    # --- LinkedIn ---
    perfil_url = Column(String(500), unique=True, index=True)

    # --- Clasificación ---
    tier = Column(String(20), nullable=True)          # ENTERPRISE / STARTER / SKIP
    query_origen = Column(String(500), nullable=True)  # La búsqueda que lo encontró

    # --- Estado y Seguimiento ---
    estado = Column(Enum(LeadStatus), default=LeadStatus.NUEVO)
    ultimo_mensaje = Column(String(2000), nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())

    def __repr__(self):
        return (
            f"<Lead(id={self.id}, nombre='{self.nombre}', "
            f"cargo='{self.cargo}', empresa='{self.empresa}', "
            f"tier='{self.tier}', estado='{self.estado.value}')>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "cargo": self.cargo,
            "empresa": self.empresa,
            "ubicacion": self.ubicacion,
            "industria": self.industria,
            "perfil_url": self.perfil_url,
            "tier": self.tier,
            "estado": self.estado.value if self.estado else None,
        }
