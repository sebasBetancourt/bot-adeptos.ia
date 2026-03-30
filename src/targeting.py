"""
Targeting System — Perfiles de Cliente Ideal + Queries de Búsqueda
Configurado según la estrategia de ventas de Ryan/AdeptosIA.

Modificar este archivo para cambiar los parámetros de búsqueda
sin tocar código del bot.
"""

# ============================================================
#  PERFILES DE BÚSQUEDA PRE-CONFIGURADOS
# ============================================================

TARGETING_PROFILES = {
    # --- ESTADOS UNIDOS (High-Ticket & Cost Reduction) ---
    "usa_real_estate": {
        "query": "Owner Real Estate Miami",
        "industria": "Real Estate",
        "region": "USA",
        "tier_default": "ENTERPRISE",
        "gancho": "Reducir el equipo de soporte de 20 a 5 personas manteniendo ventas de 8 cifras",
    },
    "usa_marketing_agency": {
        "query": "Founder Marketing Agency scaling",
        "industria": "Marketing Agency",
        "region": "USA",
        "tier_default": "ENTERPRISE",
        "gancho": "Empresas similares pierden un 21% de conversión por falta de respuesta inmediata",
    },
    "usa_saas_sales": {
        "query": "Director of Sales Software as a Service",
        "industria": "SaaS",
        "region": "USA",
        "tier_default": "ENTERPRISE",
        "gancho": "Reducir el equipo de soporte de 20 a 5 personas",
    },
    "usa_ecommerce_auto": {
        "query": "Founder E-commerce Automotive",
        "industria": "E-commerce",
        "region": "USA",
        "tier_default": "ENTERPRISE",
        "gancho": "Empresas similares pierden un 21% de conversión por falta de respuesta inmediata",
    },

    # --- COLOMBIA (Lead Leakage & Professionalization) ---
    "col_constructoras": {
        "query": "Gerente Comercial Constructora Bogotá",
        "industria": "Constructora",
        "region": "Colombia",
        "tier_default": "STARTER",
        "gancho": "No dejes que tus leads se enfríen después de las 6 PM",
    },
    "col_hoteles": {
        "query": "Director de Ventas Hotelería Colombia",
        "industria": "Hotelería",
        "region": "Colombia",
        "tier_default": "STARTER",
        "gancho": "No dejes que tus leads se enfríen después de las 6 PM",
    },
    "col_concesionarios": {
        "query": "Dueño Concesionario autos Colombia",
        "industria": "Concesionario",
        "region": "Colombia",
        "tier_default": "STARTER",
        "gancho": "No dejes que tus leads se enfríen después de las 6 PM",
    },
}


# ============================================================
#  REGLAS DE CLASIFICACIÓN (Python puro — $0 de costo)
# ============================================================

ENTERPRISE_KEYWORDS = {
    "cargos": [
        "ceo", "founder", "co-founder", "head of sales", "vp of sales",
        "chief", "director", "president", "owner", "partner",
    ],
    "industrias": [
        "real estate", "saas", "software", "marketing agency",
        "e-commerce", "fintech", "healthcare", "insurance",
    ],
    "ubicaciones": [
        "miami", "new york", "los angeles", "san francisco",
        "austin", "dallas", "chicago", "houston",
    ],
}

STARTER_KEYWORDS = {
    "cargos": [
        "gerente", "gerente comercial", "director de ventas",
        "dueño", "manager", "coordinador", "jefe de ventas",
    ],
    "industrias": [
        "constructora", "hotelería", "hotel", "concesionario",
        "automotriz", "inmobiliaria", "restaurante",
    ],
    "ubicaciones": [
        "bogotá", "medellín", "cali", "barranquilla",
        "cartagena", "bucaramanga", "colombia",
    ],
}

# Cargos que indican que la persona NO es decisor de compra → SKIP
SKIP_KEYWORDS = [
    "intern", "pasante", "practicante", "junior", "student",
    "estudiante", "freelance", "unemployed", "desempleado",
    "looking for", "buscando empleo", "open to work",
]
