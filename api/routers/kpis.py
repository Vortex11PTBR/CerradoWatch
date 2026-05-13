"""Endpoints de KPIs — mart_cerrado_kpis."""
import pandas as pd
from fastapi import APIRouter
from sqlalchemy import text

from api.database import get_engine

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/kpis")
def kpis():
    """KPIs principais do Cerrado: queimadas, desmatamento e preços (linha única)."""
    sql = """
        SELECT latest_fire_week, latest_week_fires, prev_week_fire_count,
               fires_wow_pct, fire_alert_active, latest_week_total_frp,
               latest_deforestation_year, latest_year_deforestation_km2,
               prev_year_deforestation_km2, deforestation_yoy_pct,
               soja_price_brl_sc, soja_mom_pct,
               milho_price_brl_sc, milho_mom_pct,
               generated_at
        FROM mart.mart_cerrado_kpis
        LIMIT 1
    """
    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df.to_dict(orient="records")[0] if not df.empty else {}
