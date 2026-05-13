"""Endpoints de queimadas — mart_fires_weekly."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Query
from sqlalchemy import text

from api.database import get_engine

router = APIRouter(prefix="/queimadas", tags=["Queimadas"])


@router.get("")
def listar_queimadas(
    year: Optional[int] = Query(None, description="Filtrar por ano"),
    limit: int = Query(52, le=500, description="Máximo de semanas retornadas"),
):
    """Série temporal semanal de focos de queimada no Cerrado."""
    where = "WHERE year = :year" if year else ""
    sql = f"""
        SELECT week_start, week_end, year, week_number,
               fire_count, high_confidence_count,
               day_fires, night_fires,
               avg_frp_mw, total_frp_mw,
               alert_threshold_exceeded, prev_week_fire_count, wow_change_pct
        FROM mart.mart_fires_weekly
        {where}
        ORDER BY week_start DESC
        LIMIT :limit
    """
    params = {"limit": limit}
    if year:
        params["year"] = year

    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    return df.to_dict(orient="records")


@router.get("/resumo")
def resumo_queimadas():
    """Último KPI de queimadas: semana mais recente."""
    sql = """
        SELECT week_start, fire_count, wow_change_pct,
               alert_threshold_exceeded, total_frp_mw
        FROM mart.mart_fires_weekly
        ORDER BY week_start DESC
        LIMIT 1
    """
    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df.to_dict(orient="records")[0] if not df.empty else {}
