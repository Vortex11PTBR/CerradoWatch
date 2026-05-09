"""Página 1 — Queimadas: série histórica semanal + mapa de focos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from dashboard.data import load_fires_raw, load_fires_weekly

st.set_page_config(page_title="Queimadas · CerradoWatch", page_icon="🔥", layout="wide")

st.title("🔥 Queimadas no Cerrado")
st.markdown(
    "Focos de calor detectados pelo satélite **VIIRS/SNPP** da NASA via API FIRMS. "
    "Dados atualizados semanalmente."
)

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

col_f1, _ = st.columns([2, 1])
with col_f1:
    df_weekly = load_fires_weekly()
    if not df_weekly.empty and "week_start" in df_weekly.columns:
        df_weekly["week_start"] = pd.to_datetime(df_weekly["week_start"])
        min_date = df_weekly["week_start"].min().date()
        max_date = df_weekly["week_start"].max().date()
        date_range = st.slider(
            "Período de análise",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="DD/MM/YYYY",
        )
        df_filtered = df_weekly[
            (df_weekly["week_start"].dt.date >= date_range[0])
            & (df_weekly["week_start"].dt.date <= date_range[1])
        ]
    else:
        df_filtered = df_weekly

st.divider()

# ---------------------------------------------------------------------------
# Gráfico de série temporal
# ---------------------------------------------------------------------------

st.subheader("📈 Focos de calor por semana")

if not df_filtered.empty:
    fig = go.Figure()

    # Área preenchida
    fig.add_trace(go.Scatter(
        x=df_filtered["week_start"],
        y=df_filtered["fire_count"],
        mode="lines",
        name="Total focos",
        line=dict(color="#f97316", width=2),
        fill="tozeroy",
        fillcolor="rgba(249,115,22,0.15)",
    ))

    # Alta confiança
    if "high_confidence_count" in df_filtered.columns:
        fig.add_trace(go.Scatter(
            x=df_filtered["week_start"],
            y=df_filtered["high_confidence_count"],
            mode="lines",
            name="Alta confiança",
            line=dict(color="#ef4444", width=1.5, dash="dot"),
        ))

    # Linha de threshold
    fig.add_hline(
        y=1000,
        line_dash="dash",
        line_color="#fbbf24",
        annotation_text="Threshold alerta (1.000)",
        annotation_position="bottom right",
    )

    # Semanas com alerta
    if "alert_threshold_exceeded" in df_filtered.columns:
        alert_weeks = df_filtered[df_filtered["alert_threshold_exceeded"] == True]
        fig.add_trace(go.Scatter(
            x=alert_weeks["week_start"],
            y=alert_weeks["fire_count"],
            mode="markers",
            name="Alerta disparado",
            marker=dict(color="#ef4444", size=8, symbol="star"),
        ))

    fig.update_layout(
        template="plotly_dark",
        height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.15),
        xaxis_title="Semana",
        yaxis_title="Focos de calor",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Métricas rápidas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total focos (período)", f"{df_filtered['fire_count'].sum():,}")
    m2.metric("Pico semanal", f"{df_filtered['fire_count'].max():,}")
    m3.metric("Média semanal", f"{df_filtered['fire_count'].mean():,.0f}")
    alertas = df_filtered.get("alert_threshold_exceeded", pd.Series()).sum() if "alert_threshold_exceeded" in df_filtered.columns else 0
    m4.metric("Semanas com alerta", f"{int(alertas)}")
else:
    st.info("Sem dados de queimadas para o período selecionado.")

st.divider()

# ---------------------------------------------------------------------------
# Distribuição por confiança / dia-noite
# ---------------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 Distribuição por confiança")
    if not df_filtered.empty and "high_confidence_count" in df_filtered.columns:
        total = df_filtered["fire_count"].sum()
        high = df_filtered["high_confidence_count"].sum()
        nominal = df_filtered.get("nominal_confidence_count", pd.Series([0])).sum()
        low = total - high - nominal

        fig_pie = px.pie(
            values=[high, nominal, low],
            names=["Alta", "Nominal", "Baixa"],
            color_discrete_sequence=["#ef4444", "#f97316", "#94a3b8"],
            hole=0.45,
        )
        fig_pie.update_layout(
            template="plotly_dark",
            height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=True,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.subheader("🌙 Dia vs Noite")
    if not df_filtered.empty and "day_fires" in df_filtered.columns:
        day = df_filtered["day_fires"].sum()
        night = df_filtered["night_fires"].sum()
        fig_dn = px.bar(
            x=["Dia", "Noite"],
            y=[day, night],
            color=["Dia", "Noite"],
            color_discrete_map={"Dia": "#fbbf24", "Noite": "#818cf8"},
        )
        fig_dn.update_layout(
            template="plotly_dark",
            height=280,
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_dn, use_container_width=True)
    else:
        st.caption("Dados dia/noite não disponíveis.")

st.divider()

# ---------------------------------------------------------------------------
# Mapa de focos
# ---------------------------------------------------------------------------

col_map_hdr, col_map_sel = st.columns([3, 1])
with col_map_hdr:
    st.subheader("🗺️ Mapa de focos de calor")
with col_map_sel:
    map_days = st.selectbox("Focos dos últimos", [7, 14, 30, 90], index=2, label_visibility="visible")
    map_days = int(map_days)

df_raw = load_fires_raw(days=map_days)

if not df_raw.empty:
    # Centro do Cerrado
    m = folium.Map(
        location=[-13.0, -50.5],
        zoom_start=5,
        tiles="CartoDB dark_matter",
    )

    # HeatMap
    heat_data = df_raw[["latitude", "longitude", "frp"]].dropna().values.tolist()
    HeatMap(
        heat_data,
        radius=12,
        blur=8,
        gradient={0.2: "#fbbf24", 0.5: "#f97316", 0.8: "#ef4444", 1.0: "#7f1d1d"},
    ).add_to(m)

    # Pontos dos focos de maior intensidade (top 50)
    top_fires = df_raw.nlargest(50, "frp")
    for _, row in top_fires.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=max(3, row["frp"] / 50),
            color="#ef4444",
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"FRP: {row['frp']:.1f} MW<br>"
                f"Confiança: {row.get('confidence', '?')}<br>"
                f"Data: {row.get('acq_date', '?')}",
                max_width=200,
            ),
        ).add_to(m)

    st_folium(m, width="100%", height=500, returned_objects=[])

    st.caption(
        f"**{len(df_raw):,}** focos plotados · "
        "HeatMap baseado no Fire Radiative Power (FRP em MW) · "
        "Pontos vermelhos = top 50 focos mais intensos"
    )
else:
    st.info("Sem dados de focos para o período selecionado.")

# ---------------------------------------------------------------------------
# Tabela de dados brutos
# ---------------------------------------------------------------------------

with st.expander("📋 Ver dados brutos"):
    if not df_raw.empty:
        _col_rename = {
            "latitude": "Latitude", "longitude": "Longitude",
            "frp": "FRP (MW)", "confidence": "Confiança",
            "acq_date": "Data detecção", "daynight": "Dia/Noite",
        }
        _conf_map = {"h": "Alta", "n": "Nominal", "l": "Baixa"}
        _dn_map = {"D": "Dia", "N": "Noite"}
        df_display = df_raw.sort_values("frp", ascending=False).head(200).copy()
        if "confidence" in df_display.columns:
            df_display["confidence"] = df_display["confidence"].map(_conf_map).fillna(df_display["confidence"])
        if "daynight" in df_display.columns:
            df_display["daynight"] = df_display["daynight"].map(_dn_map).fillna(df_display["daynight"])
        df_display = df_display.rename(columns=_col_rename)
        st.dataframe(df_display, use_container_width=True)
