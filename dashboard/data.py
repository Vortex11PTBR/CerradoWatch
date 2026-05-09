"""
Camada de acesso a dados do dashboard CerradoWatch.

Todas as funções retornam DataFrames pandas e são cacheadas por 1 hora.
Quando o banco não está disponível, retornam dados de amostra para demo.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Engine SQLAlchemy — criado uma vez por sessão
# ---------------------------------------------------------------------------

@st.cache_resource
def get_engine():
    """Cria engine SQLAlchemy reutilizável. Retorna None se DB indisponível."""
    try:
        from sqlalchemy import create_engine, text

        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "cerradowatch")
        user = os.getenv("POSTGRES_USER", "cerrado_user")
        password = os.getenv("POSTGRES_PASSWORD", "")

        raw_url = os.getenv("DATABASE_URL", "")
        if raw_url:
            # Neon/Render fornecem postgresql://, SQLAlchemy precisa do driver
            url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        else:
            url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

        engine = create_engine(url, pool_pre_ping=True, pool_size=2)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        return None


def _query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Executa query e retorna DataFrame. Raises se engine indisponível."""
    engine = get_engine()
    if engine is None:
        raise ConnectionError("Banco de dados indisponível")
    return pd.read_sql(sql, engine, params=params)


# ---------------------------------------------------------------------------
# KPIs — cabeçalho do dashboard
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_kpis() -> pd.DataFrame:
    try:
        return _query("SELECT * FROM mart.mart_cerrado_kpis LIMIT 1")
    except Exception:
        return _sample_kpis()


def _sample_kpis() -> pd.DataFrame:
    return pd.DataFrame([{
        "latest_fire_week": date(2026, 5, 5),
        "latest_week_fires": 1_247,
        "prev_week_fire_count": 983,
        "fires_wow_pct": 26.9,
        "fire_alert_active": True,
        "latest_week_total_frp": 18_432.5,
        "latest_deforestation_year": 2024,
        "latest_year_deforestation_km2": 8_341.0,
        "prev_year_deforestation_km2": 7_980.0,
        "deforestation_yoy_pct": 4.5,
        "soja_price_brl_sc": 139.40,
        "soja_mom_pct": -2.1,
        "milho_price_brl_sc": 55.80,
        "milho_mom_pct": 1.3,
        "generated_at": pd.Timestamp.now(),
    }])


# ---------------------------------------------------------------------------
# Queimadas — série semanal
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_fires_weekly() -> pd.DataFrame:
    try:
        df = _query("""
            SELECT week_start, week_end, year, week_number,
                   fire_count, high_confidence_count, nominal_confidence_count,
                   day_fires, night_fires,
                   avg_frp_mw, max_frp_mw, total_frp_mw,
                   alert_threshold_exceeded, wow_change_pct
            FROM mart.mart_fires_weekly
            ORDER BY week_start
        """)
        df["week_start"] = pd.to_datetime(df["week_start"])
        return df
    except Exception:
        return _sample_fires_weekly()


def _sample_fires_weekly() -> pd.DataFrame:
    weeks = pd.date_range("2024-01-01", periods=70, freq="W-MON")
    import numpy as np
    rng = np.random.default_rng(42)
    counts = (
        rng.integers(200, 600, size=40).tolist()
        + rng.integers(800, 2500, size=20).tolist()  # pico queimadas (jul-out)
        + rng.integers(150, 400, size=10).tolist()
    )
    return pd.DataFrame({
        "week_start": weeks,
        "fire_count": counts,
        "high_confidence_count": [int(c * 0.35) for c in counts],
        "nominal_confidence_count": [int(c * 0.45) for c in counts],
        "day_fires": [int(c * 0.65) for c in counts],
        "night_fires": [int(c * 0.35) for c in counts],
        "avg_frp_mw": [round(c * 0.14, 1) for c in counts],
        "total_frp_mw": [round(c * 14.2, 1) for c in counts],
        "alert_threshold_exceeded": [c >= 1000 for c in counts],
        "wow_change_pct": [None] + [
            round((counts[i] - counts[i-1]) / counts[i-1] * 100, 1)
            for i in range(1, len(counts))
        ],
    })


# ---------------------------------------------------------------------------
# Focos brutos — para o mapa
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_fires_raw(days: int = 30) -> pd.DataFrame:
    try:
        cutoff = date.today() - timedelta(days=days)
        df = _query(
            """
            SELECT latitude, longitude, frp, confidence, acq_date, daynight
            FROM raw.firms_fire_events
            WHERE acq_date >= %(cutoff)s
            ORDER BY frp DESC
            LIMIT 5000
            """,
            {"cutoff": str(cutoff)},
        )
        return df
    except Exception:
        return _sample_fires_raw()


def _sample_fires_raw() -> pd.DataFrame:
    import numpy as np
    rng = np.random.default_rng(7)
    n = 200
    # Coordenadas dentro do Cerrado (bbox: lon -60 a -41, lat -24 a -2)
    return pd.DataFrame({
        "latitude": rng.uniform(-24, -2, n).round(4),
        "longitude": rng.uniform(-60, -41, n).round(4),
        "frp": rng.uniform(5, 250, n).round(1),
        "confidence": rng.choice(["h", "n", "l"], n, p=[0.35, 0.50, 0.15]),
        "acq_date": pd.date_range(end=date.today(), periods=n, freq="3h").date,
        "daynight": rng.choice(["D", "N"], n, p=[0.7, 0.3]),
    })


# ---------------------------------------------------------------------------
# Desmatamento — anual por estado
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_deforestation() -> pd.DataFrame:
    try:
        df = _query("""
            SELECT year, state_code, area_km2,
                   prev_year_area_km2, yoy_change_pct, cumulative_area_km2,
                   rank_within_year
            FROM mart.mart_deforestation_annual
            ORDER BY year, rank_within_year
        """)
        return df
    except Exception:
        return _sample_deforestation()


def _sample_deforestation() -> pd.DataFrame:
    states = ["MT", "GO", "BA", "MG", "MS", "TO", "PI", "MA", "SP", "DF"]
    years = list(range(2015, 2025))
    import numpy as np
    rng = np.random.default_rng(1)
    rows = []
    for year in years:
        for state in states:
            base = {"MT": 2800, "GO": 1200, "BA": 900, "MG": 750, "MS": 600,
                    "TO": 500, "PI": 400, "MA": 450, "SP": 180, "DF": 40}[state]
            trend = 1.0 + (year - 2015) * 0.03
            area = round(base * trend * rng.uniform(0.85, 1.15), 1)
            rows.append({"year": year, "state_code": state, "area_km2": area})
    # Total bioma
    for year in years:
        total = sum(r["area_km2"] for r in rows if r["year"] == year)
        rows.append({"year": year, "state_code": "BR_CERRADO", "area_km2": round(total, 1)})
    df = pd.DataFrame(rows)
    df["yoy_change_pct"] = df.groupby("state_code")["area_km2"].pct_change() * 100
    df["prev_year_area_km2"] = df.groupby("state_code")["area_km2"].shift(1)
    df["rank_within_year"] = df[df["state_code"] != "BR_CERRADO"].groupby("year")["area_km2"].rank(ascending=False)
    return df


# ---------------------------------------------------------------------------
# Clima — médias mensais
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_climate(state: Optional[str] = None) -> pd.DataFrame:
    try:
        where = "WHERE state_code = %(state)s" if state else ""
        df = _query(
            f"""
            SELECT year_month, state_code, year, month,
                   avg_temp_max_c, avg_temp_min_c, avg_temp_c,
                   total_precipitation_mm, avg_humidity_pct,
                   dry_days_count, drought_risk_flag, station_count
            FROM mart.mart_climate_monthly
            {where}
            ORDER BY year_month, state_code
            """,
            {"state": state} if state else None,
        )
        df["year_month"] = pd.to_datetime(df["year_month"])
        return df
    except Exception:
        return _sample_climate(state)


def _sample_climate(state: Optional[str] = None) -> pd.DataFrame:
    import numpy as np
    states = [state] if state else ["GO", "MT", "MS"]
    months = pd.date_range("2024-01-01", periods=16, freq="MS")
    rows = []
    for s in states:
        # Semente única por estado — dados diferentes por estado
        rng = np.random.default_rng(abs(hash(s)) % (2 ** 31))
        for m in months:
            month_n = m.month
            # Sazonalidade do Cerrado: seco (abr-set), chuvoso (out-mar)
            is_dry = 4 <= month_n <= 9
            rows.append({
                "year_month": m,
                "state_code": s,
                "year": m.year,
                "month": month_n,
                "avg_temp_max_c": round(32 + rng.uniform(-3, 3) + (3 if is_dry else 0), 1),
                "avg_temp_min_c": round(18 + rng.uniform(-2, 2), 1),
                "avg_temp_c": round(25 + rng.uniform(-2, 2) + (2 if is_dry else 0), 1),
                "total_precipitation_mm": round(max(0, rng.normal(15 if is_dry else 180, 30)), 1),
                "avg_humidity_pct": round(35 + rng.uniform(-5, 5) if is_dry else 70 + rng.uniform(-8, 8), 1),
                "dry_days_count": rng.integers(20, 30) if is_dry else rng.integers(3, 12),
                "drought_risk_flag": 1 if is_dry and rng.random() > 0.4 else 0,
                "station_count": rng.integers(8, 20),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Preços agrícolas
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_prices(product: Optional[str] = None) -> pd.DataFrame:
    try:
        where = "WHERE product = %(product)s" if product else ""
        df = _query(
            f"""
            SELECT reference_month, product, state_code, year, month,
                   avg_price_per_sack_brl, avg_price_per_ton_brl,
                   mom_change_pct, prev_month_price
            FROM mart.mart_prices_monthly
            {where}
            ORDER BY reference_month, product, state_code
            """,
            {"product": product} if product else None,
        )
        df["reference_month"] = pd.to_datetime(df["reference_month"])
        return df
    except Exception:
        return _sample_prices(product)


def _sample_prices(product: Optional[str] = None) -> pd.DataFrame:
    import numpy as np
    rng = np.random.default_rng(5)
    products = [product] if product else ["soja", "milho", "algodao"]
    states = ["GO", "MT", "MS", "MG", "BA"]
    months = pd.date_range("2022-01-01", periods=40, freq="MS")
    base_price = {"soja": 140, "milho": 58, "algodao": 120}
    rows = []
    for p in products:
        for st in states:
            price = base_price.get(p, 100) * np.random.default_rng(abs(hash(st + p)) % 2**31).uniform(0.9, 1.1)
            for m in months:
                price = max(50, price * (1 + rng.normal(0, 0.03)))
                rows.append({
                    "reference_month": m,
                    "product": p,
                    "state_code": st,
                    "year": m.year,
                    "month": m.month,
                    "avg_price_per_sack_brl": round(price, 2),
                    "avg_price_per_ton_brl": round(price * 1000 / 60, 2),
                    "mom_change_pct": round(rng.normal(0, 3), 1),
                })
    return pd.DataFrame(rows)
