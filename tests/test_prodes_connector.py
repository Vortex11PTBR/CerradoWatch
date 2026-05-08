"""Testes para o conector PRODES."""
from unittest.mock import MagicMock, patch

import pytest

from ingestion.prodes.schema import ProdesRecord


class TestProdesSchema:
    def test_valid_record(self):
        r = ProdesRecord(year=2022, state="GO", area_km2=1234.5)
        assert r.year == 2022
        assert r.state == "GO"
        assert r.area_km2 == 1234.5
        assert r.biome == "Cerrado"

    def test_state_normalized_to_upper(self):
        r = ProdesRecord(year=2020, state="go", area_km2=100.0)
        assert r.state == "GO"

    def test_year_parsed_from_string(self):
        r = ProdesRecord(year="2019", state="MT", area_km2=500.0)  # type: ignore[arg-type]
        assert r.year == 2019

    def test_invalid_year_raises(self):
        with pytest.raises(Exception):
            ProdesRecord(year=1990, state="GO", area_km2=100.0)  # year < 2000


class TestProdesConnector:
    def test_normalize_state_sigla(self):
        from ingestion.prodes.connector import _normalize_state
        assert _normalize_state("GO") == "GO"

    def test_normalize_state_full_name(self):
        from ingestion.prodes.connector import _normalize_state
        assert _normalize_state("goias") == "GO"
        assert _normalize_state("Mato Grosso") == "MT"

    @patch("ingestion.prodes.connector.requests.get")
    def test_fetch_deforestation_success(self, mock_get: MagicMock):
        mock_get.return_value.json.return_value = {
            "features": [
                {"properties": {"year": 2022, "state": "GO", "area_km": "1500.5"}},
                {"properties": {"year": 2022, "state": "MT", "area_km": "2000.0"}},
                {"properties": {"year": 2022, "state": "AM", "area_km": "100.0"}},  # fora do Cerrado
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()

        from ingestion.prodes.connector import fetch_deforestation
        records = fetch_deforestation(start_year=2022, end_year=2022)

        assert len(records) == 2
        states = {r.state for r in records}
        assert "GO" in states
        assert "MT" in states
        assert "AM" not in states

    @patch("ingestion.prodes.connector.requests.get")
    def test_fetch_deforestation_default_year(self, mock_get: MagicMock):
        """Cobre o branch where end_year is None (usa datetime.today)."""
        mock_get.return_value.json.return_value = {"features": []}
        mock_get.return_value.raise_for_status = MagicMock()

        from ingestion.prodes.connector import fetch_deforestation
        records = fetch_deforestation(start_year=2022)  # end_year padrão = este ano - 1
        assert isinstance(records, list)

    @patch("ingestion.prodes.connector.requests.get")
    def test_fetch_handles_invalid_feature(self, mock_get: MagicMock):
        mock_get.return_value.json.return_value = {
            "features": [
                {"properties": {"year": "invalid", "state": "GO", "area_km": "100"}},
                {"properties": {"year": 2022, "state": "GO", "area_km": "500"}},
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()

        from ingestion.prodes.connector import fetch_deforestation
        records = fetch_deforestation(start_year=2022, end_year=2022)
        assert len(records) == 1
