# ── Stage 1: build deps ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Dependências de sistema para psycopg2 e compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python em camada separada (aproveita cache)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
        requests \
        pandas \
        python-dotenv \
        pydantic \
        pydantic-settings \
        sqlalchemy \
        psycopg2-binary \
        loguru \
        openpyxl \
        streamlit \
        plotly \
        folium \
        streamlit-folium \
        numpy


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Só libpq para psycopg2 em runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copia deps instaladas do builder
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia código da aplicação
COPY ingestion/     ./ingestion/
COPY orchestration/ ./orchestration/
COPY dashboard/     ./dashboard/
COPY data/          ./data/
COPY .streamlit/    ./.streamlit/
COPY scripts/       ./scripts/

# Usuário não-root
RUN useradd -m -u 1000 cerrado
USER cerrado

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
