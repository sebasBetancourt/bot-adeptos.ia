import os
import time
from fpdf import FPDF
from src.core.database import db_manager
from src.domain.models import Report

class ReportService:
    def __init__(self):
        self.output_dir = "reports"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_revenue_leak_audit(self, lead_data: dict) -> str:
        """
        Generates a PDF Audit highlighting $8,500/mo leak using fpdf2.
        Saves path to `reports` PostgreSQL table.
        Returns the absolute filepath.
        """
        empresa = lead_data.get("empresa", "N/A")
        # Si no detectó empresa en la web, pones "Tu Empresa"
        if not empresa or empresa == "N/A":
            empresa = "Tu Empresa"

        nombre = lead_data.get("nombre", "Líder de Ventas")

        pdf = FPDF()
        pdf.add_page()
        
        # Encabezado
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, f"Auditoría de Fuga de Ingresos: {empresa}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)
        
        # Cuerpo
        pdf.set_font("helvetica", "", 12)
        text = (
            f"Hola {nombre},\n\n"
            f"Hemos analizado el perfil comercial de {empresa} aplicando el framework avanzado de Sales Enablement de Corey Haines. "
            f"Detectamos que el estándar general de la industria sufre por deficiencias de "
            f"velocidad de respuesta a los leads comerciales (Speed-to-Lead).\n\n"
            f"MÉTRICA DE RIESGO: Un retraso superior a 5 minutos en responder a un prospecto "
            f"cuesta, en base al perfil de leads Enterprise, un aproximado de $8,500 dolares al mes "
            f"debido al enfriamiento de oportunidades en el embudo.\n\n"
            f"VENTAJAS DE RESOLVER EL 'REVENUE LEAK':\n"
            f"- Respuesta calificada instantanea.\n"
            f"- Ingesta inteligente de leads hacia bases de datos.\n"
            f"- Agendamiento validado automáticamente.\n\n"
            f"Recomendamos agendar una Discovery Call para tapar esta fuga financiera."
        )
        
        company_research = lead_data.get("company_research", "")
        if company_research:
            text += (
                f"\n\n--- INTELIGENCIA DE MERCADO (Tavily AI) ---\n"
                f"Hemos extraído la siguiente información reciente sobre {empresa}:\n"
                f"{company_research}\n\n"
                f"Dado este contexto, la automatización del embudo B2B con IA es clave para escalar su modelo de negocio sin aumentar drásticamente el costo operativo."
            )
            
        pdf.multi_cell(0, 10, text)
        
        # Pie de página
        pdf.ln(15)
        pdf.set_font("helvetica", "I", 10)
        pdf.cell(0, 10, "Generado de manera autonoma por tu Agente de Ventas IA (Adeptos)", new_x="LMARGIN", new_y="NEXT", align="C")
        
        # Guardar archivo
        timestamp = int(time.time())
        filename = f"{empresa.replace(' ','_').lower()}_audit_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        pdf.output(filepath)
        
        # Sincronizar reporte con la Base de Datos (PostgreSQL)
        self._save_report_to_db("Revenue Leak Audit", filepath, text)
        
        return filepath
        
    def _save_report_to_db(self, tipo_reporte: str, file_path: str, resumen: str):
        db = next(db_manager.get_session())
        try:
            nuevo_reporte = Report(
                tipo_reporte=tipo_reporte,
                file_path=file_path,
                resumen_hallazgos=resumen[:500]
            )
            db.add(nuevo_reporte)
            db.commit()
            print(f"--- [REPORTS DB] Auditoría PDF conectada y respaldada. ---")
        except Exception as e:
            db.rollback()
            print(f"--- [REPORTS DB ERROR] Fallo guardando Reporte: {e} ---")
        finally:
            db.close()
