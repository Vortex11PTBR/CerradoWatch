"""Endpoints de clima — mart_climate_monthly."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Query
from sqlalchemy import text

from api.database import get_engine

router = APIRouter(prefix="/clima", tags=["Clima"])


@router.get("")
def listar_clima(
    state_code: Optional[str] = Query(None, description="Ex: GO, MT, BA"),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    limit: int = Query(100, le=1000),
):
    """Médias mensais de temperatura, precipitação e umidade por estado (INMET)."""
    conditions = []
    params: dict = {"limit": limit}
    if state_code:
        conditions.append("state_code = :state_code")
        params["state_code"] = state_code.upper()
    if year:
        conditions.append("year = :year")
        params["year"] = year
    if month:
        conditions.append("month = :month")
        params["month"] = month

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT year_month, state_code, year, month,
               avg_temp_max_c, avg_temp_min_c, avg_temp_c, peak_temp_max_c,
               total_precipitation_mm, dry_days_count,
               avg_humidity_pct, avg_wind_speed_ms,
               drought_risk_flag, station_count
        FROM mart.mart_climate_monthly
        {where}
        ORDER BY year_month DESC, state_code
        LIMIT :limit
    """
    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df.to_dict(orient="records")


@router.get("/seca")
def alertas_seca():
    """Meses com flag de risco de seca ativo (temp alta + pouca chuva + baixa umidade)."""
    sql = """
        SELECT year_month, state_code, avg_temp_max_c,
               total_precipitation_mm, avg_humidity_pct
        FROM mart.mart_climate_monthly
        WHERE drought_risk_flag = 1
        ORDER BY year_month DESC
        LIMIT 100
    """
    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df.to_dict(orient="records")
