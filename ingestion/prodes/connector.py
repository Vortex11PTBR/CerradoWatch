"""
Conector PRODES — ingere dados de desmatamento do Cerrado via TerraBrasilis.

API: https://terrabrasilis.dpi.inpe.br/geoserver/prodes-cerrado-nb/ows (WFS)
Produto: incremento anual de desmatamento por estado no bioma Cerrado.
Atualização: anual (divulgado geralmente em abril do ano seguinte)
"""
from __future__ import annotations

import time

import requests
from loguru import logger
from sqlalchemy.dialects.postgresql import insert

from ingestion.database import SessionLocal, engine
from ingestion.models import ProdesDeforestation
from ingestion.prodes.schema import ProdesRecord

# WFS endpoint do TerraBrasilis para desmatamento no Cerrado
TERRABRASILIS_WFS = (
    "https://terrabrasilis.dpi.inpe.br/geoserver/prodes-cerrado-nb/ows"
)

# Estados do Cerrado monitorados
CERRADO_STATES = ["GO", "MT", "MS", "MG", "BA", "TO", "SP", "PR", "PI", "MA", "DF"]


def fetch_deforestation(start_year: int = 2010, end_year: int | None = None) -> list[ProdesRecord]:
    """
    Consulta a API WFS do TerraBrasilis e retorna incrementos de desmatamento.

    Os dados são agregados por ano e estado (granularidade suficiente para o dashboard).
    """
    import datetime
    if end_year is None:
        end_year = datetime.date.today().year - 1  # ano fechado mais recente

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "prodes-cerrado-nb:yearly_deforestation_biome",
        "outputFormat": "application/json",
        "CQL_FILTER": f"year>={start_year} AND year<={end_year}",
        # propertyName removido — causava 400 em alguns servidores WFS
    }

    logger.info(f"Consultando TerraBrasilis PRODES | anos {start_year}–{end_year}")
    response = requests.get(TERRABRASILIS_WFS, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()
    features = data.get("features", [])
    records: list[ProdesRecord] = []
    errors = 0

    for feat in features:
        props = feat.get("properties", {})
        try:
            state_raw = props.get("state", "")
            # Normaliza: TerraBrasilis pode retornar nome completo ou sigla
            state = _normalize_state(str(state_raw))
            if state not in CERRADO_STATES:
                continue
            records.append(ProdesRecord(
                year=props["year"],
                state=state,
                area_km2=float(props.get("area_km", 0) or 0),
                municipality=props.get("municipality", ""),
                biome="Cerrado",
            ))
        except Exception as e:
            logger.warning(f"Feature PRODES inválida ignorada: {e} | props={props}")
            errors += 1

    logger.info(f"PRODES: {len(records)} registros | {errors} erros")
    return records


def _normalize_state(raw: str) -> str:
    """Converte nome completo de estado para sigla quando necessário."""
    name_to_uf = {
        "goias": "GO", "mato grosso": "MT", "mato grosso do sul": "MS",
        "minas gerais": "MG", "bahia": "BA", "tocantins": "TO",
        "sao paulo": "SP", "parana": "PR", "piaui": "PI",
        "maranhao": "MA", "distrito federal": "DF",
    }
    cleaned = raw.lower().strip()
    return name_to_uf.get(cleaned, raw.upper()[:2])


def upsert_deforestation(records: list[ProdesRecord]) -> int:
    """Insere dados de desmatamento com upsert por (year, state, municipality)."""
    if not records:
        return 0

    rows = [
        {
            "year": r.year,
            "state": r.state,
            "municipality": r.municipality,
            "area_km2": r.area_km2,
            "biome": r.biome,
            "class_name": r.class_name,
        }
        for r in records
    ]

    stmt = insert(ProdesDeforestation).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_prodes_year_state_mun",
        set_={"area_km2": stmt.excluded.area_km2},
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()
        logger.info(f"PRODES: {result.rowcount} registros inseridos/atualizados")
        return result.rowcount


def run(start_year: int = 2010) -> int:
    """Pipeline completo PRODES."""
    ProdesDeforestation.metadata.create_all(engine)
    records = fetch_deforestation(start_year=start_year)
    return upsert_deforestation(records)


if __name__ == "__main__":
    count = run()
    logger.info(f"Pipeline PRODES concluído. {count} registros.")
