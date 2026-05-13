"""Endpoints de desmatamento — mart_deforestation_annual."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Query
from sqlalchemy import text

from api.database import get_engine

router = APIRouter(prefix="/desmatamento", tags=["Desmatamento"])


@router.get("")
def listar_desmatamento(
    state_code: Optional[str] = Query(None, description="Ex: GO, MT, BR_CERRADO"),
    year: Optional[int] = Query(None, description="Filtrar por ano"),
):
    """Desmatamento anual por estado no Cerrado (PRODES/INPE)."""
    conditions = []
    params: dict = {}
    if state_code:
        conditions.append("state_code = :state_code")
        params["state_code"] = state_code.upper()
    if year:
        conditions.append("year = :year")
        params["year"] = year

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT year, state_code, area_km2,
               prev_year_area_km2, yoy_change_pct,
               cumulative_area_km2, rank_within_year
        FROM mart.mart_deforestation_annual
        {where}
        ORDER BY year DESC, area_km2 DESC
    """
    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df.to_dict(orient="records")


@router.get("/estados")
def ranking_estados(year: Optional[int] = Query(None)):
    """Ranking de estados por desmatamento no ano mais recente (ou filtrado)."""
    year_filter = "AND year = :year" if year else ""
    params: dict = {}
    if year:
        params["year"] = year

    sql = f"""
        SELECT year, state_code, area_km2, yoy_change_pct, rank_within_year
        FROM mart.mart_deforestation_annual
        WHERE state_code != 'BR_CERRADO' {year_filter}
        ORDER BY year DESC, rank_within_year ASC
        LIMIT 50
    """
    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df.to_dict(orient="records")
