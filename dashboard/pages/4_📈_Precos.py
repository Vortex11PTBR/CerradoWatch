"""Página 4 — Preços: commodities agrícolas e correlação com desmatamento."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.data import load_deforestation, load_prices

st.set_page_config(page_title="Preços · CerradoWatch", page_icon="📈", layout="wide")

st.title("📈 Commodities Agrícolas")
st.markdown(
    "Preços mensais de **soja, milho e algodão** — principais commodities cultivadas "
    "no Cerrado. A correlação entre valorização das commodities e expansão do desmatamento "
    "é uma das hipóteses centrais do projeto."
)

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

CERRADO_STATES = ["GO", "MT", "MS", "MG", "BA", "TO", "SP", "PI", "MA", "DF"]
PRODUCTS = ["soja", "milho", "algodao"]

col_f1, col_f2 = st.columns([1, 1])
with col_f1:
    selected_products = st.multiselect("Commodities", PRODUCTS, default=["soja", "milho"])
with col_f2:
    selected_state = st.selectbox("Estado de referência", CERRADO_STATES, index=0)

df_prices = load_prices()

if df_prices.empty:
    st.warning("Dados de preços não disponíveis.")
    st.stop()

import pandas as pd
df_prices["reference_month"] = pd.to_datetime(df_prices["reference_month"])

df_filtered = df_prices[
    (df_prices["product"].isin(selected_products))
    & (df_prices["state_code"] == selected_state)
].sort_values("reference_month")

st.divider()

# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

cols = st.columns(len(selected_products) * 2 or 1)
for i, product in enumerate(selected_products):
    df_p = df_filtered[df_filtered["product"] == product]
    if df_p.empty:
        continue
    latest = df_p.iloc[-1]
    price = latest.get("avg_price_per_sack_brl", 0) or 0
    mom = latest.get("mom_change_pct", 0) or 0
    with cols[i * 2]:
        st.metric(
            f"{product.capitalize()} (R$/sc)",
            f"R$ {price:.2f}",
            f"{mom:+.1f}% MoM",
            delta_color="normal",
        )
    with cols[i * 2 + 1]:
        ton = price * 1000 / 60 if price else 0
        st.metric(f"{product.capitalize()} (R$/ton)", f"R$ {ton:,.0f}")

st.divider()

# ---------------------------------------------------------------------------
# Gráfico de série histórica de preços
# ---------------------------------------------------------------------------

st.subheader("💰 Série histórica de preços")

if not df_filtered.empty:
    fig = go.Figure()
    colors = {"soja": "#fbbf24", "milho": "#4ade80", "algodao": "#818cf8"}

    for product in selected_products:
        df_p = df_filtered[df_filtered["product"] == product].sort_values("reference_month")
        if df_p.empty:
            continue
        fig.add_trace(go.Scatter(
            x=df_p["reference_month"],
            y=df_p["avg_price_per_sack_brl"],
            name=product.capitalize(),
            mode="lines+markers",
            line=dict(color=colors.get(product, "#94a3b8"), width=2),
            marker=dict(size=4),
        ))

    fig.update_layout(
        template="plotly_dark",
        height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Mês",
        yaxis_title="R$/sc 60kg",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Variação MoM
# ---------------------------------------------------------------------------

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 Variação mensal (MoM)")
    if not df_filtered.empty:
        df_mom = df_filtered.dropna(subset=["mom_change_pct"]).copy()
        df_mom["color"] = df_mom["mom_change_pct"].apply(
            lambda v: "#ef4444" if v > 0 else "#4ade80"
        )
        for product in selected_products:
            df_p = df_mom[df_mom["product"] == product].tail(12)
            if df_p.empty:
                continue
            fig_mom = px.bar(
                df_p,
                x="reference_month",
                y="mom_change_pct",
                title=f"{product.capitalize()} — variação % MoM (últimos 12 meses)",
                color="mom_change_pct",
                color_continuous_scale=["#4ade80", "#f8fafc", "#ef4444"],
                color_continuous_midpoint=0,
                labels={"mom_change_pct": "%", "reference_month": "Mês"},
            )
            fig_mom.update_layout(
                template="plotly_dark",
                height=260,
                margin=dict(l=0, r=0, t=30, b=0),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_mom, use_container_width=True)

with col2:
    st.subheader("🔗 Correlação: soja × desmatamento")
    st.markdown(
        "_Hipótese: anos com preço de soja mais alto incentivam expansão do agronegócio "
        "sobre o Cerrado, aumentando o desmatamento._"
    )

    df_def = load_deforestation()
    df_soja = df_prices[
        (df_prices["product"] == "soja") & (df_prices["state_code"] == selected_state)
    ].copy()

    if not df_def.empty and not df_soja.empty:
        # Agrega preço médio anual de soja
        df_soja["year"] = df_soja["reference_month"].dt.year
        soja_annual = df_soja.groupby("year")["avg_price_per_sack_brl"].mean().reset_index()
        soja_annual.columns = ["year", "avg_soja_price"]

        # Desmatamento total do bioma por ano
        defor_annual = df_def[df_def["state_code"] == "BR_CERRADO"][["year", "area_km2"]].copy()

        corr_df = pd.merge(soja_annual, defor_annual, on="year", how="inner")

        if len(corr_df) >= 3:
            fig_corr = px.scatter(
                corr_df,
                x="avg_soja_price",
                y="area_km2",
                text="year",
                trendline="ols",
                labels={
                    "avg_soja_price": "Preço médio soja (R$/sc)",
                    "area_km2": "Desmatamento (km²)",
                },
                color_discrete_sequence=["#fbbf24"],
            )
            fig_corr.update_traces(
                textposition="top center",
                selector=dict(mode="markers+text"),
            )
            fig_corr.update_layout(
                template="plotly_dark",
                height=380,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_corr, use_container_width=True)

            # Coeficiente de correlação
            corr_val = corr_df["avg_soja_price"].corr(corr_df["area_km2"])
            st.metric(
                "Correlação de Pearson (soja × desmatamento)",
                f"r = {corr_val:.3f}",
                "Positiva forte (>0.7)" if corr_val > 0.7
                else "Positiva moderada" if corr_val > 0.4
                else "Fraca / sem correlação",
                delta_color="off",
            )
        else:
            st.info("Dados insuficientes para calcular correlação.")
    else:
        st.info("Carregue dados de desmatamento e preços para ver a correlação.")

# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------

with st.expander("📋 Ver dados brutos de preços"):
    st.dataframe(
        df_prices[df_prices["product"].isin(selected_products)]
        .sort_values("reference_month", ascending=False)
        .head(200),
        use_container_width=True,
    )
