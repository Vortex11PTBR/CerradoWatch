"""Página 2 — Desmatamento: série histórica + ranking por estado."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.data import load_deforestation

st.set_page_config(page_title="Desmatamento · CerradoWatch", page_icon="🌳", layout="wide")

st.title("🌳 Desmatamento no Cerrado")
st.markdown(
    "Incremento anual de desmatamento detectado pelo **PRODES/INPE** via TerraBrasilis. "
    "Série histórica a partir de 2010."
)

df = load_deforestation()

if df.empty:
    st.warning("Dados de desmatamento não disponíveis.")
    st.stop()

# Separa total do bioma e dados por estado
df_total = df[df["state_code"] == "BR_CERRADO"].copy()
df_states = df[df["state_code"] != "BR_CERRADO"].copy()

years = sorted(df_states["year"].dropna().unique().tolist(), reverse=True)
states = sorted(df_states["state_code"].dropna().unique().tolist())

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

col_f1, col_f2 = st.columns([3, 1])
with col_f1:
    selected_year = st.select_slider("Ano de referência", options=sorted(years), value=max(years))
with col_f2:
    selected_states = st.multiselect("Filtrar estados", states, default=states)

df_year = df_states[
    (df_states["year"] == selected_year)
    & (df_states["state_code"].isin(selected_states))
].sort_values("area_km2", ascending=False)

st.divider()

# ---------------------------------------------------------------------------
# Linha 1: métricas
# ---------------------------------------------------------------------------

total_year = df_total[df_total["year"] == selected_year]["area_km2"].values
total_prev = df_total[df_total["year"] == selected_year]["prev_year_area_km2"].values
yoy = df_total[df_total["year"] == selected_year]["yoy_change_pct"].values

m1, m2, m3, m4 = st.columns(4)
m1.metric(
    f"Desmatamento {selected_year}",
    f"{total_year[0]:,.0f} km²" if len(total_year) else "—",
    f"{yoy[0]:+.1f}% YoY" if len(yoy) and yoy[0] else None,
    delta_color="inverse",
)
m2.metric(
    "Maior desmatador",
    df_year.iloc[0]["state_code"] if not df_year.empty else "—",
    f"{df_year.iloc[0]['area_km2']:,.0f} km²" if not df_year.empty else None,
    delta_color="off",
)
m3.metric(
    "Estados com alta (>800km²)",
    str(len(df_year[df_year["area_km2"] > 800])),
)
equiv = (total_year[0] / 5765) if len(total_year) else 0
m4.metric("Equivale a", f"{equiv:.0f}× Brasília", "km² destruídos")

st.divider()

# ---------------------------------------------------------------------------
# Col 1: Ranking por estado (ano selecionado)
# ---------------------------------------------------------------------------

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(f"📊 Ranking por estado — {selected_year}")
    if not df_year.empty:
        fig_bar = px.bar(
            df_year,
            x="area_km2",
            y="state_code",
            orientation="h",
            color="area_km2",
            color_continuous_scale="YlOrRd",
            labels={"area_km2": "km² desmatados", "state_code": "Estado"},
            text=df_year["area_km2"].apply(lambda v: f"{v:,.0f}"),
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(l=0, r=60, t=10, b=0),
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("📉 Série histórica — total do Cerrado")
    if not df_total.empty:
        df_total_plot = df_total.sort_values("year")
        fig_line = go.Figure()
        fig_line.add_trace(go.Bar(
            x=df_total_plot["year"],
            y=df_total_plot["area_km2"],
            name="Desmatamento (km²)",
            marker_color=[
                "#ef4444" if (row.get("yoy_change_pct") or 0) > 5
                else "#f97316" if (row.get("yoy_change_pct") or 0) > 0
                else "#4ade80"
                for _, row in df_total_plot.iterrows()
            ],
        ))
        # Marca o ano selecionado
        fig_line.add_vline(
            x=selected_year,
            line_dash="dash",
            line_color="#818cf8",
            annotation_text=str(selected_year),
        )
        fig_line.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Ano",
            yaxis_title="km² desmatados",
            hovermode="x",
        )
        st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Evolução por estado (treemap)
# ---------------------------------------------------------------------------

st.subheader(f"🗂️ Proporção por estado — {selected_year}")
if not df_year.empty:
    fig_tm = px.treemap(
        df_year,
        path=["state_code"],
        values="area_km2",
        color="area_km2",
        color_continuous_scale="YlOrRd",
        hover_data={"area_km2": ":.0f"},
    )
    fig_tm.update_traces(textinfo="label+value+percent root")
    fig_tm.update_layout(
        template="plotly_dark",
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_tm, use_container_width=True)

# ---------------------------------------------------------------------------
# Tendência por estado
# ---------------------------------------------------------------------------

st.subheader("📈 Tendência histórica por estado")
df_trend = df_states[df_states["state_code"].isin(selected_states)].sort_values("year")

fig_trend = px.line(
    df_trend,
    x="year",
    y="area_km2",
    color="state_code",
    markers=True,
    labels={"area_km2": "km² desmatados", "year": "Ano", "state_code": "Estado"},
)
fig_trend.update_layout(
    template="plotly_dark",
    height=360,
    margin=dict(l=0, r=0, t=10, b=0),
    hovermode="x unified",
)
st.plotly_chart(fig_trend, use_container_width=True)

# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------

with st.expander("📋 Ver tabela completa"):
    st.dataframe(
        df_states[df_states["state_code"].isin(selected_states)]
        .sort_values(["year", "area_km2"], ascending=[False, False])
        .style.format({"area_km2": "{:,.1f}", "yoy_change_pct": "{:+.1f}%"}),
        use_container_width=True,
    )
