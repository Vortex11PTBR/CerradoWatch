"""Página principal — CerradoWatch Dashboard."""
import sys
from pathlib import Path

# Garante que o repo root está no sys.path (necessário no Streamlit Cloud)
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="CerradoWatch",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS customizado
st.markdown("""
<style>
    .kpi-box {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        border-left: 4px solid #4ade80;
    }
    .kpi-label { color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; letter-spacing: .05em; }
    .kpi-value { color: #f1f5f9; font-size: 1.8rem; font-weight: 700; margin: 4px 0; }
    .kpi-delta-pos { color: #f87171; font-size: 0.85rem; }
    .kpi-delta-neg { color: #4ade80; font-size: 0.85rem; }
    .kpi-delta-neu { color: #94a3b8; font-size: 0.85rem; }
    .alert-banner {
        background: #7f1d1d;
        border: 1px solid #ef4444;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin-bottom: 1rem;
    }
    section[data-testid="stSidebar"] { background: #0f172a; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.image(
        "https://img.shields.io/badge/CerradoWatch-v1.0-4ade80?style=for-the-badge",
        use_container_width=True,
    )
    st.markdown("### 🌿 CerradoWatch")
    st.markdown("""
Plataforma de monitoramento ambiental do Cerrado com **dados abertos do governo federal**.

**Fontes:**
- 🛰️ FIRMS/NASA — queimadas
- 🌳 PRODES/INPE — desmatamento
- 🌡️ INMET — clima
- 📊 CONAB — commodities

**Atualização:** toda segunda-feira
""")
    st.divider()
    st.caption("Dados: INPE · INMET · CONAB · NASA FIRMS")
    st.caption("Pipeline: Python · dbt · PostgreSQL · FastAPI · Docker · GitHub Actions")


# ---------------------------------------------------------------------------
# Carrega KPIs
# ---------------------------------------------------------------------------

from dashboard.data import load_kpis  # noqa: E402

kpis = load_kpis()
k = kpis.iloc[0]

# ---------------------------------------------------------------------------
# Alerta de queimadas
# ---------------------------------------------------------------------------

if k.get("fire_alert_active"):
    st.markdown("""
<div class="alert-banner">
⚠️ <strong>ALERTA DE QUEIMADAS ATIVO</strong> — Volume semanal de focos acima do threshold.
&nbsp;·&nbsp; <a href="./Queimadas" target="_self" style="color:#fff;font-weight:bold;text-decoration:underline;">🔥 Ver Queimadas</a>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🌿 CerradoWatch")
st.markdown(
    "**Monitoramento ambiental do Cerrado** — "
    "o segundo maior bioma do Brasil, responsável por 70% da água doce do país."
)

# ---------------------------------------------------------------------------
# KPI cards — linha 1: queimadas
# ---------------------------------------------------------------------------

st.markdown("#### 🔥 Queimadas")
c1, c2, c3, c4 = st.columns(4)

fires = int(k.get("latest_week_fires", 0) or 0)
fires_prev = int(k.get("prev_week_fire_count", 0) or 0)
fires_delta = float(k.get("fires_wow_pct", 0) or 0)
frp = float(k.get("latest_week_total_frp", 0) or 0)

with c1:
    delta_class = "kpi-delta-pos" if fires_delta > 10 else ("kpi-delta-neg" if fires_delta < -5 else "kpi-delta-neu")
    delta_icon = "▲" if fires_delta > 0 else "▼"
    st.markdown(f"""
<div class="kpi-box">
  <div class="kpi-label">Focos esta semana</div>
  <div class="kpi-value">{fires:,}</div>
  <div class="{delta_class}">{delta_icon} {abs(fires_delta):.1f}% vs semana anterior</div>
</div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
<div class="kpi-box" style="border-left-color:#f97316">
  <div class="kpi-label">FRP total (MW)</div>
  <div class="kpi-value">{frp:,.0f}</div>
  <div class="kpi-delta-neu">Fire Radiative Power — energia liberada</div>
</div>""", unsafe_allow_html=True)

with c3:
    alert_text = "🚨 ALERTA ATIVO" if k.get("fire_alert_active") else "✅ Normal"
    alert_color = "#ef4444" if k.get("fire_alert_active") else "#4ade80"
    st.markdown(f"""
<div class="kpi-box" style="border-left-color:{alert_color}">
  <div class="kpi-label">Status do alerta</div>
  <div class="kpi-value" style="font-size:1.3rem">{alert_text}</div>
  <div class="kpi-delta-neu">Limite: 1.000 focos/semana</div>
</div>""", unsafe_allow_html=True)

week = k.get("latest_fire_week", "—")
with c4:
    st.markdown(f"""
<div class="kpi-box" style="border-left-color:#818cf8">
  <div class="kpi-label">Semana de referência</div>
  <div class="kpi-value" style="font-size:1.2rem">{week}</div>
  <div class="kpi-delta-neu">Última semana completa</div>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# KPI cards — linha 2: desmatamento e preços
# ---------------------------------------------------------------------------

st.markdown("#### 🌳 Desmatamento & Commodities")
c1, c2, c3, c4 = st.columns(4)

defor = float(k.get("latest_year_deforestation_km2", 0) or 0)
defor_prev = float(k.get("prev_year_deforestation_km2", 0) or 0)
defor_yoy = float(k.get("deforestation_yoy_pct", 0) or 0)

with c1:
    d_class = "kpi-delta-pos" if defor_yoy > 0 else "kpi-delta-neg"
    d_icon = "▲" if defor_yoy > 0 else "▼"
    st.markdown(f"""
<div class="kpi-box" style="border-left-color:#a3e635">
  <div class="kpi-label">Desmatamento {int(k.get("latest_deforestation_year", 0) or 0)}</div>
  <div class="kpi-value">{defor:,.0f} km²</div>
  <div class="{d_class}">{d_icon} {abs(defor_yoy):.1f}% vs ano anterior</div>
</div>""", unsafe_allow_html=True)

with c2:
    brasilia_ref = defor_prev or 1
    equiv = defor / 5765 * 100  # Brasília = 5.765 km²
    st.markdown(f"""
<div class="kpi-box" style="border-left-color:#a3e635">
  <div class="kpi-label">Equivalente a</div>
  <div class="kpi-value" style="font-size:1.2rem">{equiv:.0f}× Brasília</div>
  <div class="kpi-delta-neu">Área destruída este ano</div>
</div>""", unsafe_allow_html=True)

soja = float(k.get("soja_price_brl_sc", 0) or 0)
soja_mom = float(k.get("soja_mom_pct", 0) or 0)
with c3:
    s_class = "kpi-delta-pos" if soja_mom > 5 else ("kpi-delta-neg" if soja_mom < -5 else "kpi-delta-neu")
    s_icon = "▲" if soja_mom > 0 else "▼"
    st.markdown(f"""
<div class="kpi-box" style="border-left-color:#fbbf24">
  <div class="kpi-label">Soja (R$/sc 60kg)</div>
  <div class="kpi-value">R$ {soja:.2f}</div>
  <div class="{s_class}">{s_icon} {abs(soja_mom):.1f}% no mês</div>
</div>""", unsafe_allow_html=True)

milho = float(k.get("milho_price_brl_sc", 0) or 0)
milho_mom = float(k.get("milho_mom_pct", 0) or 0)
with c4:
    m_class = "kpi-delta-pos" if milho_mom > 5 else ("kpi-delta-neg" if milho_mom < -5 else "kpi-delta-neu")
    m_icon = "▲" if milho_mom > 0 else "▼"
    st.markdown(f"""
<div class="kpi-box" style="border-left-color:#fbbf24">
  <div class="kpi-label">Milho (R$/sc 60kg)</div>
  <div class="kpi-value">R$ {milho:.2f}</div>
  <div class="{m_class}">{m_icon} {abs(milho_mom):.1f}% no mês</div>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Rodapé
# ---------------------------------------------------------------------------

st.divider()

import pandas as _pd
generated = k.get("generated_at", None)
try:
    ts = _pd.Timestamp(generated)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    iso_utc = ts.isoformat()
except Exception:
    iso_utc = ""

if iso_utc:
    components.html(f"""
<span id="cw-ts" style="color:#94a3b8;font-size:0.8rem;">🕐 Dados atualizados em: carregando...</span>
<script>
(function() {{
    var dt = new Date("{iso_utc}");
    var fmt = dt.toLocaleString(undefined, {{
        day:"2-digit", month:"2-digit", year:"numeric",
        hour:"2-digit", minute:"2-digit",
        timeZoneName:"short"
    }});
    document.getElementById("cw-ts").textContent = "🕐 Dados atualizados em: " + fmt;
}})();
</script>
""", height=28)
else:
    st.caption(f"🕐 Dados atualizados em: {generated or '—'}")

st.caption(
    "Fonte: NASA FIRMS · INPE/PRODES · INMET · CONAB · "
    "Pipeline: [github.com/Vortex11PTBR/CerradoWatch](https://github.com/Vortex11PTBR/CerradoWatch)"
)
