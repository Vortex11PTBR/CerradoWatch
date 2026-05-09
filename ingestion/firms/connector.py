"""
Conector FIRMS — ingere focos de queimada do Cerrado via NASA FIRMS API.

Documentação da API: https://firms.modaps.eosdis.nasa.gov/api/area/
Produto usado: VIIRS_SNPP_NRT (Near Real-Time, latência ~3h)
Área do Cerrado (bounding box): lon_min=-60, lat_min=-24, lon_max=-41, lat_max=-2
"""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta

import requests
from loguru import logger
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from ingestion.config import settings
from ingestion.database import SessionLocal, engine
from ingestion.firms.models import FirmsFireEvent
from ingestion.firms.schema import FirmsFireRecord

# Bounding box do Cerrado (graus decimais)
CERRADO_BBOX = "-60,-24,-41,-2"  # lon_min, lat_min, lon_max, lat_max

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
PRODUCT = "VIIRS_SNPP_NRT"


def fetch_fires(days: int = 7) -> list[FirmsFireRecord]:
    """Consulta a API FIRMS e retorna focos de queimada nos últimos N dias."""
    map_key = settings.firms_map_key.strip()  # remove newlines acidentais do secret
    url = f"{FIRMS_BASE_URL}/{map_key}/{PRODUCT}/{CERRADO_BBOX}/{days}"
    logger.info(f"Consultando FIRMS API | produto={PRODUCT} | dias={days}")

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text))
    records: list[FirmsFireRecord] = []
    errors = 0

    for row in reader:
        try:
            records.append(FirmsFireRecord(**row))
        except Exception as e:
            logger.warning(f"Linha inválida ignorada: {e} | linha={row}")
            errors += 1

    logger.info(f"FIRMS: {len(records)} registros válidos | {errors} ignorados")
    return records


def load_from_csv(csv_text: str) -> list[FirmsFireRecord]:
    """Carrega registros a partir de um CSV já baixado (útil para testes)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    records = []
    for row in reader:
        try:
            records.append(FirmsFireRecord(**row))
        except Exception as e:
            logger.warning(f"Linha inválida: {e}")
    return records


def upsert_fires(records: list[FirmsFireRecord]) -> int:
    """
    Insere focos no PostgreSQL (raw.firms_fire_events).
    Usa upsert por (latitude, longitude, acq_date, acq_time) para evitar duplicatas
    em execuções repetidas.
    """
    if not records:
        logger.warning("Nenhum registro para inserir.")
        return 0

    rows = [
        {
            "latitude": r.latitude,
            "longitude": r.longitude,
            "bright_ti4": r.bright_ti4,
            "scan": r.scan,
            "track": r.track,
            "acq_date": r.acq_date,
            "acq_time": r.acq_time,
            "satellite": r.satellite,
            "instrument": r.instrument,
            "confidence": r.confidence,
            "version": r.version,
            "bright_ti5": r.bright_ti5,
            "frp": r.frp,
            "daynight": r.daynight,
        }
        for r in records
    ]

    stmt = insert(FirmsFireEvent).values(rows)
    stmt = stmt.on_conflict_do_nothing()  # idempotente

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()
        inserted = result.rowcount
        logger.info(f"Inseridos {inserted} novos focos no raw.firms_fire_events")
        return inserted


def ensure_table() -> None:
    """Cria a tabela raw.firms_fire_events se não existir."""
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
    FirmsFireEvent.metadata.create_all(engine)
    logger.info("Tabela raw.firms_fire_events verificada/criada.")


def run(days: int = 7) -> int:
    """Executa o pipeline completo: fetch → validate → load."""
    ensure_table()
    records = fetch_fires(days=days)
    return upsert_fires(records)


if __name__ == "__main__":
    count = run()
    logger.info(f"Pipeline FIRMS concluído. {count} registros novos.")
