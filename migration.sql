-- ==============================================================================
-- AI MARKETING CO-PILOT (Total Assistant) - Arquitectura Empresarial PostgreSQL
-- ==============================================================================
-- Autor: Antigravity (Data Arch)
-- Propósito: Estructurar la persistencia de datos analíticos y tracking de
--            ventas (Leads, Reuniones, Reportes, Métricas) basados en el 
--            framework de Outbound de Corey Haines.
-- ==============================================================================

-- 1. LIMPIEZA INICIAL (DESACTIVADA PARA EVITAR PÉRDIDA DE DATOS)
-- Solo descomenta si deseas resetear TODA la base de datos desde cero.
-- DROP TABLE IF EXISTS metrics CASCADE;
-- DROP TABLE IF EXISTS reports CASCADE;
-- DROP TABLE IF EXISTS meetings CASCADE;
-- DROP TABLE IF EXISTS leads CASCADE;
-- DROP TABLE IF EXISTS chat_history CASCADE;
-- DROP TABLE IF EXISTS admin_users CASCADE;
-- DROP TYPE IF EXISTS lead_status CASCADE;

-- 2. TIPOS PERSONALIZADOS (ENUMS)
-- Representa el embudo de prospección exacto por el que cruza un bot.
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lead_status') THEN
        CREATE TYPE lead_status AS ENUM (
            'NUEVO',
            'CALIFICADO',
            'DESCARTADO',
            'PENDIENTE_MENSAJE',
            'CONTACTADO',
            'RESPONDIO',
            'REUNION_AGENDADA'
        );
    END IF;
END $$;

-- 3. CREACIÓN DE TABLAS

-- TABLA: LEADS (Prospectos)
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    cargo VARCHAR(255),
    empresa VARCHAR(255),
    industria VARCHAR(255),
    linkedin_url VARCHAR(500) UNIQUE, -- Garantiza ser la llave única anti-duplicados
    ubicacion VARCHAR(255),
    lead_score INTEGER DEFAULT 0,     -- Score basado en Framework Corey Haines (0 a 100)
    tier VARCHAR(50),                 -- Clasificación: ENTERPRISE, STARTER
    query_origen VARCHAR(500),        -- Términos de búsqueda del Scraper
    estado lead_status DEFAULT 'NUEVO',
    ultimo_mensaje TEXT,              -- Último mensaje de Outreach inyectado
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TABLA: MEETINGS (Reuniones)
CREATE TABLE IF NOT EXISTS meetings (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE, -- Foreign Key
    fecha_hora TIMESTAMP NOT NULL,
    tipo_evento VARCHAR(100),         -- ej: Auditoría Inicial, Discovery Call
    enlace_reunion VARCHAR(500),      -- ej: Teams o Calendly dinámico
    notas TEXT,                       -- Resumen o apuntes clave de la persona
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TABLA: REPORTS (Archivos y Reportajes Extraídos)
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    tipo_reporte VARCHAR(100) NOT NULL, -- ej: LinkedIn Audit, Market Analysis
    file_path VARCHAR(500) NOT NULL,    -- Ruta del PDF o archivo local
    resumen_hallazgos TEXT,             -- Conclusiones hechas por el LLM (Sonnet)
    creado_por VARCHAR(100) DEFAULT 'SAAM',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TABLA: ADMIN USERS (Auth RBAC)
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) UNIQUE NOT NULL,
    descripcion VARCHAR(100) DEFAULT 'Administrador'
);

-- TABLA: CHAT HISTORY (Memoria Conversacional de WhatsApp)
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,          -- 'user', 'ai', o 'system'
    content TEXT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TABLA: METRICS (Estadísticas y KPIs del mes)
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    mes_año VARCHAR(20) NOT NULL,                  -- Periodo, ej. '2026-03'
    leads_generados INTEGER DEFAULT 0,
    reuniones_agendadas INTEGER DEFAULT 0,
    tasa_conversion NUMERIC(5,2) DEFAULT 0.00,     -- ej: 12.50 (%)
    revenue_proyectado NUMERIC(15,2) DEFAULT 0.00, -- Cálculo de Fuga ($8,500/mo) * Conversiones
    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. CREACIÓN DE ÍNDICES PARA RENDIMIENTO
-- Aceleran dramáticamente las búsquedas y deduplicaciones del Bot
CREATE INDEX IF NOT EXISTS idx_leads_linkedin ON leads(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_leads_estado ON leads(estado);
CREATE INDEX IF NOT EXISTS idx_meetings_fecha ON meetings(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_chat_phone ON chat_history(phone_number);

-- 5. DATOS DE PRUEBA (SEED DATA)
-- Poblar las tablas para análisis inmediato de métricas

-- ADMINISTRADORES (Sebas)
INSERT INTO admin_users (phone_number, descripcion) VALUES
('whatsapp:+573046417789', 'Sebas (Jefe de Operaciones)')
ON CONFLICT (phone_number) DO NOTHING;

-- TABLA: MICROSOFT AUTH (Persistencia de Tokens OAuth2)
CREATE TABLE IF NOT EXISTS microsoft_auth (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) UNIQUE NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    scope TEXT,
    tenant_id VARCHAR(100),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO meetings (lead_id, fecha_hora, tipo_evento, enlace_reunion, notas) VALUES
(3, '2026-04-02 10:00:00', 'Discovery Call', 'https://calendly.com/adeptos/discovery', 'Target prioritario. Validar la métrica exacta de leads perdidos mensuales.'),
(4, '2026-04-05 14:30:00', 'Auditoría', 'https://calendly.com/adeptos/audit', 'Andrea quiere sistematizar respuestas y cotizaciones después de las 6PM.'),
(5, '2026-04-01 09:00:00', 'Cierre Técnico', 'https://teams.microsoft.com/l/meetup-join/...', 'Presentar ROI proyectado en base a $8,500 de revenue leak mitigado.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO metrics (mes_año, leads_generados, reuniones_agendadas, tasa_conversion, revenue_proyectado) VALUES
('2026-03', 150, 12, 8.00, 102000.00)
ON CONFLICT DO NOTHING;

-- ADMINISTRADORES (Sebas)
INSERT INTO admin_users (phone_number, descripcion) VALUES
('whatsapp:+573046417789', 'Sebas (Jefe de Operaciones)')
ON CONFLICT (phone_number) DO NOTHING;
