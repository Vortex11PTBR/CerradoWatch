-- Inicialização do banco CerradoWatch
-- Este script roda automaticamente na primeira vez que o container sobe

-- Schema para dados brutos (chegam da ingestão sem transformação)
CREATE SCHEMA IF NOT EXISTS raw;

-- Schema para dados transformados pelo dbt (staging + mart)
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS mart;

-- Extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- busca textual eficiente

-- Tabela de controle de execução dos pipelines
CREATE TABLE IF NOT EXISTS raw.pipeline_runs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source      VARCHAR(50) NOT NULL,       -- firms, prodes, inmet, conab
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status      VARCHAR(20) NOT NULL DEFAULT 'running', -- running, success, failed
    records_loaded INTEGER,
    error_msg   TEXT,
    metadata    JSONB
);

COMMENT ON SCHEMA raw     IS 'Dados brutos da ingestão — nunca modificar manualmente';
COMMENT ON SCHEMA staging IS 'Dados limpos e tipados pelo dbt — camada staging';
COMMENT ON SCHEMA mart    IS 'Tabelas analíticas finais — consumidas pelo dashboard';
