"""
Conector INMET — estações meteorológicas e observações diárias do Cerrado.

API: https://apitempo.inmet.gov.br/
Endpoints usados:
  - GET /estacoes/T          → lista todas estações automáticas
  - GET /estacao/diaria/{ini}/{fim}/{cod}  → dados diários por estação

Documentação: https://portal.inmet.gov.br/manual/manual-de-uso-da-api-do-inmet
"""
from __future__ import annotations

import time
from datetime import date, timedelta

import requests
from loguru import logger
from sqlalchemy.dialects.postgresql import insert

from ingestion.database import SessionLocal, engine
from ingestion.inmet.schema import InmetDailyRecord, InmetStationRecord
from ingestion.models import InmetDailyObservation, InmetStation

INMET_BASE = "https://apitempo.inmet.gov.br"

# Estados do Cerrado — para filtrar estações relevantes
CERRADO_STATES = {"GO", "MT", "MS", "MG", "BA", "TO", "SP", "PI", "MA", "DF"}

# Mapeamento de campos da API para o schema interno
FIELD_MAP = {
    "TEM_MAX": "temp_max_c",
    "TEM_MIN": "temp_min_c",
    "TEM_INS": "temp_avg_c",
    "CHUVA": "precipitation_mm",
    "UMD_MED": "humidity_pct",
    "VEN_VEL": "wind_speed_ms",
}


def fetch_stations() -> list[InmetStationRecord]:
    """Busca todas as estações automáticas e filtra as do Cerrado."""
    url = f"{INMET_BASE}/estacoes/T"
    logger.info("Buscando estações INMET automáticas...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    stations: list[InmetStationRecord] = []
    for item in resp.json():
        state = str(item.get("SG_ESTADO", "")).upper()
        if state not in CERRADO_STATES:
            continue
        try:
            stations.append(InmetStationRecord(
                station_code=item["CD_ESTACAO"],
                station_name=item.get("DC_NOME", ""),
                state=state,
                latitude=float(item.get("VL_LATITUDE", 0) or 0),
                longitude=float(item.get("VL_LONGITUDE", 0) or 0),
                altitude_m=float(item["VL_ALTITUDE"]) if item.get("VL_ALTITUDE") else None,
                station_type="T",
            ))
        except Exception as e:
            logger.warning(f"Estação INMET inválida ignorada: {e}")

    logger.info(f"INMET: {len(stations)} estações no Cerrado encontradas")
    return stations


def upsert_stations(stations: list[InmetStationRecord]) -> int:
    """Insere/atualiza metadados de estações."""
    if not stations:
        return 0
    rows = [
        {
            "station_code": s.station_code,
            "station_name": s.station_name,
            "state": s.state,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "altitude_m": s.altitude_m,
            "station_type": s.station_type,
        }
        for s in stations
    ]
    stmt = insert(InmetStation).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["station_code"],
        set_={"station_name": stmt.excluded.station_name,
              "latitude": stmt.excluded.latitude,
              "longitude": stmt.excluded.longitude},
    )
    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()
        return result.rowcount


def fetch_daily_observations(
    station: InmetStationRecord,
    start_date: date,
    end_date: date,
) -> list[InmetDailyRecord]:
    """Busca observações diárias de uma estação entre start_date e end_date."""
    url = (
        f"{INMET_BASE}/estacao/diaria"
        f"/{start_date.strftime('%Y-%m-%d')}"
        f"/{end_date.strftime('%Y-%m-%d')}"
        f"/{station.station_code}"
    )
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Estação {station.station_code} sem dados: {e}")
        return []

    records: list[InmetDailyRecord] = []
    for item in resp.json() or []:
        try:
            records.append(InmetDailyRecord(
                station_code=station.station_code,
                state=station.state,
                measure_date=item.get("DT_MEDICAO", ""),
                temp_max_c=item.get("TEM_MAX"),
                temp_min_c=item.get("TEM_MIN"),
                temp_avg_c=item.get("TEM_INS"),
                precipitation_mm=item.get("CHUVA"),
                humidity_pct=item.get("UMD_MED"),
                wind_speed_ms=item.get("VEN_VEL"),
            ))
        except Exception as e:
            logger.debug(f"Observação inválida ignorada: {e}")
    return records


def upsert_observations(records: list[InmetDailyRecord]) -> int:
    """Upsert idempotente de observações diárias."""
    if not records:
        return 0
    rows = [
        {
            "station_code": r.station_code,
            "measure_date": r.measure_date,
            "state": r.state,
            "temp_max_c": r.temp_max_c,
            "temp_min_c": r.temp_min_c,
            "temp_avg_c": r.temp_avg_c,
            "precipitation_mm": r.precipitation_mm,
            "humidity_pct": r.humidity_pct,
            "wind_speed_ms": r.wind_speed_ms,
        }
        for r in records
    ]
    stmt = insert(InmetDailyObservation).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_inmet_station_date")
    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()
        return result.rowcount


def run(days_back: int = 30, max_stations: int | None = None) -> int:
    """Pipeline completo INMET: estações → observações dos últimos N dias."""
    InmetStation.metadata.create_all(engine)
    InmetDailyObservation.metadata.create_all(engine)

    stations = fetch_stations()
    if max_stations:
        stations = stations[:max_stations]
    upsert_stations(stations)

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back)

    total = 0
    for i, station in enumerate(stations):
        records = fetch_daily_observations(station, start_date, end_date)
        total += upsert_observations(records)
        if i < len(stations) - 1:
            time.sleep(0.3)  # respeita rate limit da API

    logger.info(f"INMET: {total} observações inseridas de {len(stations)} estações")
    return total


if __name__ == "__main__":
    count = run(days_back=7)
    logger.info(f"Pipeline INMET concluído. {count} registros.")
