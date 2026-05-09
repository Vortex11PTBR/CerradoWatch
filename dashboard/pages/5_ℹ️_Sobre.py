"""Página 5 — Sobre o projeto CerradoWatch."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Sobre · CerradoWatch", page_icon="ℹ️", layout="wide")

st.title("ℹ️ Sobre o CerradoWatch")
st.markdown(
    "**Plataforma de monitoramento ambiental do Cerrado** — "
    "dados públicos, infraestrutura real, impacto real."
)

st.divider()

# ---------------------------------------------------------------------------
# O problema
# ---------------------------------------------------------------------------

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("🌿 O Problema")
    st.markdown("""
O **Cerrado** é o segundo maior bioma do Brasil:

- Responsável por **70% da água doce** do país (nasce aqui o Pantanal, o Araguaia, o São Francisco)
- Está sendo destruído **mais rapidamente que a Amazônia**
- Tem **dez vezes menos visibilidade** na mídia e nas políticas públicas

Os dados existem e são públicos — **INPE, IBGE, INMET, CONAB** — mas estão dispersos,
em formatos difíceis e inacessíveis para jornalistas, ONGs e pesquisadores.

**CerradoWatch conecta tudo isso** em um pipeline automatizado que transforma
dados brutos em informação acionável, atualizada toda semana.
""")

with col2:
    st.subheader("📊 Números do projeto")
    st.metric("Atualização", "Semanal (automática)")
    st.metric("Fontes de dados", "4 APIs públicas")
    st.metric("Satélite FIRMS", "VIIRS/SNPP — latência ~3h")
    st.metric("Cobertura histórica", "2010 → hoje")

st.divider()

# ---------------------------------------------------------------------------
# Fontes de dados
# ---------------------------------------------------------------------------

st.subheader("🛰️ Fontes de Dados")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
**🔥 Queimadas — NASA FIRMS**
- Produto: VIIRS SNPP Near Real-Time
- Resolução: 375m, latência ~3 horas
- Cobertura: bounding box do Cerrado (-60,-24,-41,-2)
- API: [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/api/area/)

**🌳 Desmatamento — INPE PRODES**
- Sistema: PRODES (Projeto de Monitoramento do Desmatamento)
- Granularidade: anual, por estado
- Bioma: Cerrado não-brasil (prodes-cerrado-nb)
- API: [TerraBrasilis WFS](https://terrabrasilis.dpi.inpe.br)
""")

with col2:
    st.markdown("""
**🌡️ Clima — INMET**
- Rede: estações automáticas nos estados do Cerrado
- Variáveis: temperatura, precipitação, umidade, vento
- Granularidade: diária por estação
- API: [apitempo.inmet.gov.br](https://apitempo.inmet.gov.br)

**📈 Commodities — CONAB**
- Produtos: soja, milho, algodão, cana
- Granularidade: mensal por produto e estado
- Relevância: preços agrícolas correlacionam com desmatamento
- Fonte: [Portal CONAB](https://portaldeinformacoes.conab.gov.br)
""")

st.divider()

# ---------------------------------------------------------------------------
# Arquitetura técnica
# ---------------------------------------------------------------------------

st.subheader("⚙️ Arquitetura Técnica")

st.markdown("""
```
[NASA FIRMS] ─┬
[INPE PRODES] ├─► [Python Ingestão] ─► [PostgreSQL raw] ─► [dbt staging/mart] ─► [Streamlit]
[INMET]       ├─►  (SQLAlchemy)         (Neon.tech)         (modelos SQL)          (este app)
[CONAB]       ─┘

GitHub Actions → pipeline semanal automático (toda segunda, 06h BRT)
```
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
**Ingestão**
- Python 3.11 + requests
- Pydantic para validação
- SQLAlchemy ORM
- Upsert idempotente (sem duplicatas)
""")

with col2:
    st.markdown("""
**Transformação**
- dbt (data build tool)
- 2 camadas: `staging` → `mart`
- SQL testável e documentado
- Materialized views no PostgreSQL
""")

with col3:
    st.markdown("""
**Visualização & Deploy**
- Streamlit Community Cloud
- Plotly (séries temporais)
- Folium (mapas interativos)
- PostgreSQL: Neon.tech (serverless)
""")

st.divider()

# ---------------------------------------------------------------------------
# Para quem é
# ---------------------------------------------------------------------------

st.subheader("👥 Para quem é este dashboard")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
**📰 Jornalistas**

Dados semanais atualizados sobre queimadas e desmatamento, prontos para
reportagens. Série histórica comparável e alertas automáticos quando
os números disparam.
""")

with col2:
    st.markdown("""
**🌱 ONGs e Pesquisadores**

Dados brutos acessíveis via interface visual, sem necessidade de
processar APIs governamentais. Exportação disponível nas tabelas
de dados brutos de cada seção.
""")

with col3:
    st.markdown("""
**💼 Tomadores de Decisão**

KPIs consolidados em tempo real — focos de calor, área desmatada,
tendências de commodities. Contexto visual que facilita priorização
de recursos e políticas.
""")

st.divider()

# ---------------------------------------------------------------------------
# Projeto aberto
# ---------------------------------------------------------------------------

st.subheader("🔓 Projeto Open Source")

st.markdown("""
CerradoWatch é **100% open source** e os dados usados são públicos do governo federal brasileiro.

- 📦 **Código:** [github.com/Vortex11PTBR/CerradoWatch](https://github.com/Vortex11PTBR/CerradoWatch)
- 📄 **Licença:** MIT — use, modifique, distribua livremente
- 🐛 **Issues / sugestões:** abra uma issue no GitHub
- 🤝 **Contribuições:** PRs são bem-vindos

**Stack:** Python · dbt · PostgreSQL · Streamlit · GitHub Actions · Docker
""")

st.info(
    "💡 Se você usa estes dados em pesquisa ou reportagem, considere citar o projeto "
    "e/ou abrir uma issue para nos contar — adoramos saber o impacto real.",
    icon="💡",
)
