# CerradoWatch 🌿🔥

> Pipeline de monitoramento ambiental do Cerrado — dados públicos, infraestrutura real, impacto real.

[![CI](https://github.com/Vortex11PTBR/CerradoWatch/actions/workflows/ci.yml/badge.svg)](https://github.com/Vortex11PTBR/CerradoWatch/actions)
[![Pipeline](https://github.com/Vortex11PTBR/CerradoWatch/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Vortex11PTBR/CerradoWatch/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![dbt](https://img.shields.io/badge/dbt-postgres-orange.svg)](https://getdbt.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## O Problema

O Cerrado é o **segundo maior bioma do Brasil**, responsável por **70% da água doce** do país. Está sendo destruído mais rapidamente que a Amazônia — mas tem dez vezes menos visibilidade. Os dados de queimadas, desmatamento e impacto climático existem e são públicos (INPE, INMET, CONAB), mas estão dispersos, sujos e inacessíveis para quem não é cientista de dados.

**CerradoWatch conecta tudo isso.**

## O que este projeto constrói

Um **pipeline de dados de produção** que ingere, transforma e visualiza dados ambientais reais:

- 🔥 **Queimadas** — API FIRMS/INPE, atualização semanal
- 🌳 **Desmatamento** — INPE/PRODES, série histórica
- 🌡️ **Clima** — INMET, estações meteorológicas do Cerrado
- 🌾 **Preços agrícolas** — CONAB, correlação com expansão do agro

## Arquitetura

```
[INPE/FIRMS] ─┬
[PRODES]      ├─► [Python Ingestion] ─► [PostgreSQL raw] ─► [dbt staging/mart] ─► [Streamlit]
[INMET]       |                                                                      (Render)
[CONAB]      ─┘
               [GitHub Actions cron — toda segunda 06:00 BRT]
                    └─► pipeline completo + dbt run + alertas e-mail
```

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Ingestão | Python 3.11, Pandas/Polars, requests |
| Warehouse | PostgreSQL 16 |
| Transformação | dbt-core + dbt-postgres |
| Orquestração | Prefect 2 |
| Visualização | Streamlit + Plotly + Folium |
| CI/CD | GitHub Actions |
| Deploy | Render |

## Setup em 3 comandos

```bash
# 1. Clone e configure variáveis
git clone https://github.com/Vortex11PTBR/CerradoWatch.git
cd CerradoWatch
cp .env.example .env  # edite com suas credenciais

# 2. Suba o banco e inicialize
make up
make install
make db-init

# 3. Rode o primeiro pipeline e abra o dashboard
make pipeline
make dashboard
```

## Deploy (Render)

1. Faça fork do repositório
2. No [Render Dashboard](https://render.com), clique em **New → Blueprint**
3. Conecte o repositório — o `render.yaml` configura tudo automaticamente:
   - Web service: Streamlit dashboard
   - PostgreSQL: banco de dados gerenciado
   - Cron job: pipeline semanal (toda segunda 06:00 BRT)
4. Configure os secrets no painel do Render:
   - `FIRMS_MAP_KEY` — obtenha em [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/api/area/)
   - `SMTP_USER` / `SMTP_PASSWORD` — Gmail App Password para alertas
   - `ALERT_EMAIL_TO` — e-mail de destino dos alertas

## Pipeline Semanal (GitHub Actions)

O pipeline também roda via GitHub Actions toda segunda-feira automaticamente.
Para executar manualmente: **Actions → Pipeline Semanal → Run workflow**.

Secrets necessários no repositório:
- `FIRMS_MAP_KEY`
- `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO` (opcional — para alertas)

## Estrutura do Projeto

```
cerradowatch/
├── ingestion/          # Conectores para cada fonte de dados
│   ├── firms/          # Queimadas (INPE/NASA FIRMS)
│   ├── prodes/         # Desmatamento (INPE PRODES)
│   ├── inmet/          # Dados climáticos
│   └── conab/          # Preços agrícolas
├── dbt/                # Modelos de transformação
│   ├── models/
│   │   ├── staging/    # Limpeza e tipagem dos dados brutos
│   │   └── mart/       # Tabelas analíticas finais
│   └── tests/          # Testes de qualidade de dados
├── dashboard/          # Aplicação Streamlit
├── orchestration/      # Flows Prefect
├── scripts/            # SQL de inicialização
└── docs/adr/           # Architecture Decision Records
```

## Decisões de Arquitetura

Ver [docs/adr/](docs/adr/) para os Architecture Decision Records.

## Impacto

Usuários reais: jornalistas de dados, ONGs ambientais, pesquisadores universitários e órgãos públicos estaduais do Cerrado.

---

Desenvolvido por [João Lacerda](https://joaolacerda.dev) · Dados: INPE, INMET, CONAB (domínio público)
