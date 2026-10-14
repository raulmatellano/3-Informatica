-- ============================================================================
-- PRÁCTICA 2: SISTEMAS INFORMÁTICOS - CURSO 2026/2027
-- ESCUELA POLITÉCNICA SUPERIOR - UNIVERSIDAD AUTÓNOMA DE MADRID
-- ARCHIVO: db_init.sql (Script unificado de inicialización y carga)
-- ============================================================================
-- ¿POR QUÉ SE HACE ASÍ?:
--   - Provee un único punto de entrada para ejecutar tanto el esquema DDL
--     como la carga DML en clientes locales o pipelines automatizados.
-- ¿CÓMO SE HACE?:
--   - Utiliza las directivas \i de PostgreSQL para incluir secuencialmente
--     schema.sql (estructura, triggers, SPs) y populate.sql (datos iniciales).
-- ¿PARA QUÉ SE HACE ASÍ?:
--   - Facilita la recreación limpia y reproducible de la base de datos completa
--     con un solo comando: psql -U alumnodb -d si1 -f db_init.sql
-- ============================================================================

\i schema.sql
\i populate.sql
