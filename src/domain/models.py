import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, func, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.core.database import Base


class LeadStatus(enum.Enum):
    NUEVO = "NUEVO"
    CALIFICADO = "CALIFICADO"
    DESCARTADO = "DESCARTADO"
    PENDIENTE_MENSAJE = "PENDIENTE_MENSAJE"
    CONTACTADO = "CONTACTADO"
    RESPONDIO = "RESPONDIO"
    REUNION_AGENDADA = "REUNION_AGENDADA"

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    # --- Datos del Perfil ---
    nombre = Column(String(255), nullable=False)
    cargo = Column(String(255), nullable=True)
    empresa = Column(String(255), nullable=True)
    industria = Column(String(255), nullable=True)

    # --- LinkedIn ---
    linkedin_url = Column(String(500), unique=True, index=True)
    ubicacion = Column(String(255), nullable=True)

    # --- Clasificación ---
    lead_score = Column(Integer, default=0)
    tier = Column(String(50), nullable=True)          # ENTERPRISE / STARTER / SKIP
    query_origen = Column(String(500), nullable=True)

    # --- Estado y Seguimiento ---
    estado = Column(Enum(LeadStatus), default=LeadStatus.NUEVO)
    ultimo_mensaje = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())
    
    # --- Relaciones ---
    meetings = relationship("Meeting", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<Lead(id={self.id}, nombre='{self.nombre}', "
            f"cargo='{self.cargo}', empresa='{self.empresa}', "
            f"tier='{self.tier}', score={self.lead_score})>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "cargo": self.cargo,
            "empresa": self.empresa,
            "industria": self.industria,
            "linkedin_url": self.linkedin_url,
            "ubicacion": self.ubicacion,
            "lead_score": self.lead_score,
            "tier": self.tier,
            "estado": self.estado.name if self.estado else None,
        }

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"))
    fecha_hora = Column(DateTime, nullable=False)
    tipo_evento = Column(String(100), nullable=True)
    enlace_reunion = Column(String(500), nullable=True)
    notas = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())

    # --- Relaciones ---
    lead = relationship("Lead", back_populates="meetings")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    tipo_reporte = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    resumen_hallazgos = Column(Text, nullable=True)
    creado_por = Column(String(100), default='SAAM')
    fecha_creacion = Column(DateTime, default=func.now())

class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    mes_año = Column(String(20), nullable=False)
    leads_generados = Column(Integer, default=0)
    reuniones_agendadas = Column(Integer, default=0)
    tasa_conversion = Column(Numeric(5, 2), default=0.00)
    revenue_proyectado = Column(Numeric(15, 2), default=0.00)
    ultima_actualizacion = Column(DateTime, default=func.now())

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(50), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime, default=func.now())

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(100), default="Administrador")

class MicrosoftAuth(Base):
    __tablename__ = "microsoft_auth"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(50), unique=True, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    scope = Column(Text)
    tenant_id = Column(String(100))
    fecha_creacion = Column(DateTime, default=func.now())
