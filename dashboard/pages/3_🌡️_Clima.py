"""Página 3 — Clima: temperatura, precipitação e risco de seca por estado."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.data import load_climate

st.set_page_config(page_title="Clima · CerradoWatch", page_icon="🌡️", layout="wide")

st.title("🌡️ Clima no Cerrado")
st.markdown(
    "Dados de estações meteorológicas automáticas do **INMET** (Instituto Nacional "
    "de Meteorologia). Temperatura, precipitação e risco de seca mensal por estado."
)

CERRADO_STATES = ["GO", "MT", "MS", "MG", "BA", "TO", "SP", "PI", "MA", "DF"]

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

col_f1, col_f2 = st.columns([1, 1])
with col_f1:
    selected_state = st.selectbox("Estado", CERRADO_STATES, index=0)
with col_f2:
    show_all = st.toggle("Comparar todos os estados", value=False)

df_state = load_climate(state=None if show_all else selected_state)

if df_state.empty:
    st.warning("Dados climáticos não disponíveis.")
    st.stop()

import pandas as pd
df_state["year_month"] = pd.to_datetime(df_state["year_month"])

st.divider()

# ---------------------------------------------------------------------------
# Se modo single-state: métricas + gráficos detalhados
# ---------------------------------------------------------------------------

if not show_all:
    df = df_state.sort_values("year_month")

    if df.empty:
        st.info(f"Sem dados para {selected_state}.")
        st.stop()

    latest = df.iloc[-1]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Temp. máx. (último mês)", f"{latest.get('avg_temp_max_c', '—')} °C")
    m2.metric("Precipitação (último mês)", f"{latest.get('total_precipitation_mm', '—')} mm")
    m3.metric("Umidade média", f"{latest.get('avg_humidity_pct', '—')}%")
    drought = latest.get("drought_risk_flag", 0)
    m4.metric("Risco de seca", "⚠️ Alto" if drought else "✅ Normal")

    st.divider()

    # Gráfico duplo: temperatura + precipitação
    st.subheader(f"📊 Temperatura e precipitação — {selected_state}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=df["year_month"], y=df["avg_temp_max_c"],
        name="Temp. máxima (°C)",
        line=dict(color="#ef4444", width=2),
        mode="lines+markers",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df["year_month"], y=df["avg_temp_min_c"],
        name="Temp. mínima (°C)",
        line=dict(color="#818cf8", width=1.5, dash="dot"),
        mode="lines",
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=df["year_month"], y=df["total_precipitation_mm"],
        name="Precipitação (mm)",
        marker_color="rgba(59,130,246,0.5)",
        marker_line_color="rgba(59,130,246,0.8)",
        marker_line_width=1,
    ), secondary_y=True)

    # Flag de seca
    drought_months = df[df["drought_risk_flag"] == 1]
    if not drought_months.empty:
        fig.add_trace(go.Scatter(
            x=drought_months["year_month"],
            y=drought_months["avg_temp_max_c"],
            mode="markers",
            name="⚠️ Risco de seca",
            marker=dict(color="#fbbf24", size=10, symbol="diamond"),
        ), secondary_y=False)

    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_yaxes(title_text="Temperatura (°C)", secondary_y=False)
    fig.update_yaxes(title_text="Precipitação (mm)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Sazonalidade — médias por mês do ano
    st.subheader("📅 Sazonalidade (média por mês do ano)")
    seasonal = df.groupby("month").agg({
        "avg_temp_max_c": "mean",
        "avg_temp_min_c": "mean",
        "total_precipitation_mm": "mean",
        "avg_humidity_pct": "mean",
        "drought_risk_flag": "sum",
    }).reset_index()

    month_names = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                   "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    seasonal["month_name"] = seasonal["month"].apply(lambda m: month_names[m - 1])

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(
        x=seasonal["month_name"], y=seasonal["total_precipitation_mm"],
        name="Precipitação média (mm)",
        marker_color="rgba(59,130,246,0.6)",
    ), secondary_y=True)
    fig2.add_trace(go.Scatter(
        x=seasonal["month_name"], y=seasonal["avg_temp_max_c"],
        name="Temp. máx. média (°C)",
        line=dict(color="#ef4444", width=2),
    ), secondary_y=False)
    fig2.update_layout(
        template="plotly_dark", height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
    )
    fig2.update_yaxes(title_text="°C", secondary_y=False)
    fig2.update_yaxes(title_text="mm", secondary_y=True)
    st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Modo comparativo — todos os estados
# ---------------------------------------------------------------------------

else:
    st.subheader("🗺️ Comparativo de temperatura máxima por estado")

    latest_per_state = (
        df_state.sort_values("year_month")
        .groupby("state_code")
        .last()
        .reset_index()
    )

    fig_comp = px.bar(
        latest_per_state.sort_values("avg_temp_max_c", ascending=False),
        x="state_code",
        y="avg_temp_max_c",
        color="avg_temp_max_c",
        color_continuous_scale="RdYlBu_r",
        labels={"avg_temp_max_c": "Temp. máx. (°C)", "state_code": "Estado"},
        text="avg_temp_max_c",
    )
    fig_comp.update_traces(texttemplate="%{text:.1f}°C", textposition="outside")
    fig_comp.update_layout(
        template="plotly_dark", height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_comp, use_container_width=True)

    st.subheader("🌧️ Precipitação acumulada por estado (último período)")
    fig_rain = px.bar(
        latest_per_state.sort_values("total_precipitation_mm", ascending=False),
        x="state_code",
        y="total_precipitation_mm",
        color="total_precipitation_mm",
        color_continuous_scale="Blues",
        labels={"total_precipitation_mm": "Precipitação (mm)", "state_code": "Estado"},
        text="total_precipitation_mm",
    )
    fig_rain.update_traces(texttemplate="%{text:.0f}mm", textposition="outside")
    fig_rain.update_layout(
        template="plotly_dark", height=360,
        margin=dict(l=0, r=0, t=10, b=0),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_rain, use_container_width=True)

# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------

with st.expander("📋 Ver dados brutos"):
    st.dataframe(df_state.sort_values("year_month", ascending=False).head(200),
                 use_container_width=True)
