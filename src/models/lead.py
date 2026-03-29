from sqlalchemy import Column, Integer, String, Enum
import enum
from src.database import Base

class LeadStatus(enum.Enum):
    NUEVO = "NUEVO"
    PENDIENTE_APROBACION = "PENDIENTE_APROBACION"
    CONTACTADO = "CONTACTADO"

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=True)
    perfil_url = Column(String(500), unique=True, index=True)
    ultimo_mensaje = Column(String(1000), nullable=True)
    estado = Column(Enum(LeadStatus), default=LeadStatus.NUEVO)

    def __repr__(self):
        return f"<Lead(id={self.id}, nombre='{self.nombre}', estado='{self.estado.value}')>"
