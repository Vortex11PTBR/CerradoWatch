# CerradoWatch 🌿🔥

> Pipeline de monitoramento ambiental do Cerrado — dados públicos, infraestrutura real, impacto real.

[![CI](https://github.com/Vortex11PTBR/CerradoWatch/actions/workflows/ci.yml/badge.svg)](https://github.com/Vortex11PTBR/CerradoWatch/actions)
[![Pipeline](https://github.com/Vortex11PTBR/CerradoWatch/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Vortex11PTBR/CerradoWatch/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![dbt](https://img.shields.io/badge/dbt-postgres-orange.svg)](https://getdbt.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

🚀 **[Dashboard ao vivo → cerradowatch-g6wx9wwwr6mwydqvjwzyue.streamlit.app](https://cerradowatch-g6wx9wwwr6mwydqvjwzyue.streamlit.app)**

## Screenshots

| Home & KPIs | Queimadas — série histórica |
|:-----------:|:---------------------------:|
| ![Home](screenshots/home.png) | ![Queimadas](screenshots/queimadas-chart.png) |

| Mapa de focos de calor | Desmatamento por estado |
|:----------------------:|:-----------------------:|
| ![Mapa](screenshots/mapa-calor.png) | ![Desmatamento](screenshots/desmatamento.png) |

| Clima & risco de seca | Preços × desmatamento (correlação) |
|:---------------------:|:----------------------------------:|
| ![Clima](screenshots/clima.png) | ![Preços](screenshots/precos-correlacao.png) |

| Arquitetura técnica |
|:-------------------:|
| ![Arquitetura](screenshots/arquitetura.png) |

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
| Ingestão | Python 3.11, requests, Pydantic |
| Warehouse | PostgreSQL (Neon.tech serverless) |
| Transformação | dbt-core + dbt-postgres |
| Orquestração | GitHub Actions (cron semanal) |
| Visualização | Streamlit + Plotly + Folium |
| CI/CD | GitHub Actions |
| Deploy | Streamlit Community Cloud + Neon |

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

## Deploy gratuito (sem cartão de crédito)

1. **Banco de dados:** crie conta em [neon.tech](https://neon.tech) → novo projeto → copie a connection string
2. **Dashboard:** faça deploy em [share.streamlit.io](https://share.streamlit.io) → conecte o repo → main file: `dashboard/app.py`
3. **Pipeline:** configure os secrets no GitHub (`DATABASE_URL`, `FIRMS_MAP_KEY`) → Actions → Pipeline Semanal

Secrets necessários:
- `DATABASE_URL` — connection string PostgreSQL (ex.: Neon)
- `FIRMS_MAP_KEY` — obtenha em [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/api/area/)
- `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO` — opcional, para alertas por e-mail

## Estrutura do Projeto

```
cerradowatch/
├── ingestion/          # Conectores para cada fonte de dados
│   ├── firms/          # Queimadas (NASA FIRMS)
│   ├── prodes/         # Desmatamento (INPE PRODES)
│   ├── inmet/          # Dados climáticos (INMET)
│   └── conab/          # Preços agrícolas (CONAB)
├── dbt/                # Modelos de transformação
│   ├── models/
│   │   ├── staging/    # Limpeza e tipagem dos dados brutos
│   │   └── mart/       # Tabelas analíticas finais
│   └── tests/          # Testes de qualidade de dados
├── dashboard/          # Aplicação Streamlit
│   └── pages/          # 🔥 Queimadas · 🌳 Desmatamento · 🌡️ Clima · 📈 Preços · ℹ️ Sobre
├── orchestration/      # Pipeline runner + alertas
└── docs/adr/           # Architecture Decision Records
```

## Decisões de Arquitetura

Ver [docs/adr/](docs/adr/) para os Architecture Decision Records.

## Impacto

Usuários reais: jornalistas de dados, ONGs ambientais, pesquisadores universitários e órgãos públicos estaduais do Cerrado.

---

Desenvolvido por [João Lacerda](https://joaolacerda.dev) · Dados: INPE, INMET, CONAB, NASA FIRMS (domínio público)
