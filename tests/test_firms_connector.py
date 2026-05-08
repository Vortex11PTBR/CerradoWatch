"""Testes do conector FIRMS — sem dependência de banco ou API."""
from pathlib import Path

import pytest

from ingestion.firms.connector import load_from_csv
from ingestion.firms.schema import FirmsFireRecord

SAMPLE_CSV = (
    Path(__file__).parent.parent / "data" / "samples" / "firms_cerrado_sample.csv"
)


def test_load_from_csv_retorna_registros():
    records = load_from_csv(SAMPLE_CSV.read_text())
    assert len(records) == 20


def test_todos_registros_sao_fire_record(firms_sample_records):
    for r in firms_sample_records:
        assert isinstance(r, FirmsFireRecord)


def test_coordenadas_dentro_do_cerrado(firms_sample_records):
    """Todos os pontos devem estar dentro do bounding box do Cerrado."""
    for r in firms_sample_records:
        assert -60.0 <= r.longitude <= -41.0, f"Longitude fora: {r.longitude}"
        assert -24.0 <= r.latitude <= -2.0, f"Latitude fora: {r.latitude}"


def test_confianca_valores_validos(firms_sample_records):
    for r in firms_sample_records:
        assert r.confidence in ("l", "n", "h")


def test_frp_positivo(firms_sample_records):
    for r in firms_sample_records:
        assert r.frp >= 0


def test_daynight_valido(firms_sample_records):
    for r in firms_sample_records:
        assert r.daynight in ("D", "N")


def test_registro_invalido_ignorado():
    """Linha com dado corrompido não deve explodir — é ignorada."""
    bad_csv = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\nnao_e_numero,-51.0,305.0,0.4,0.4,2026-05-08,449,N,VIIRS,n,2.0NRT,289.0,1.0,N\n"
    records = load_from_csv(bad_csv)
    assert len(records) == 0


@pytest.fixture
def firms_sample_records() -> list[FirmsFireRecord]:
    return load_from_csv(SAMPLE_CSV.read_text())
