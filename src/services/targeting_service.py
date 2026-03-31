"""
Targeting Service — OOP Wrapper for Target and Classification logic.
"""

class TargetingService:
    TARGETING_PROFILES = {
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

    SKIP_KEYWORDS = [
        "intern", "pasante", "practicante", "junior", "student",
        "estudiante", "freelance", "unemployed", "desempleado",
        "looking for", "buscando empleo", "open to work",
    ]

    @classmethod
    def get_enterprise_keywords(cls):
        return cls.ENTERPRISE_KEYWORDS
        
    @classmethod
    def get_starter_keywords(cls):
        return cls.STARTER_KEYWORDS
        
    @classmethod
    def get_skip_keywords(cls):
        return cls.SKIP_KEYWORDS
