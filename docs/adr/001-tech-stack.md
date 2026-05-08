# ADR 001 — Decisão de Stack Técnica

**Status:** Aceito  
**Data:** 2026-05  
**Contexto:** CerradoWatch precisa de um pipeline confiável para dados governamentais abertos.

## Decisão

| Componente | Escolha | Alternativas Consideradas | Motivo |
|---|---|---|---|
| Linguagem | Python 3.11+ | R, Scala | Ecossistema de dados, facilidade de manutenção |
| Warehouse | PostgreSQL 16 | BigQuery, DuckDB | Custo zero, self-hosted, suporte dbt nativo |
| Transformação | dbt | SQL puro, Spark | Data lineage, testes declarativos, documentação automática |
| Orquestração | Prefect | Airflow, Dagster | Menor overhead operacional, UI moderna |
| Dashboard | Streamlit | Metabase, Superset | Python nativo, deploy simples, baixo custo |
| Deploy | Render | AWS, Railway | Free tier generoso, deploy via Git, PostgreSQL managed |

## Consequências

- PostgreSQL no Render tem limite de 1GB no free tier — suficiente para MVP (dados históricos comprimidos)
- Prefect Cloud free tier cobre 3 execuções simultâneas — suficiente para 4 pipelines semanais
- Streamlit Community Cloud é gratuito para repositórios públicos
