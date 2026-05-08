"""Testes para o conector INMET."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ingestion.inmet.schema import InmetDailyRecord, InmetStationRecord


class TestInmetSchema:
    def test_valid_station(self):
        s = InmetStationRecord(
            station_code="A001",
            station_name="Brasília",
            state="DF",
            latitude=-15.79,
            longitude=-47.93,
        )
        assert s.station_code == "A001"
        assert s.state == "DF"

    def test_daily_record_valid(self):
        r = InmetDailyRecord(
            station_code="A001",
            measure_date=date(2024, 6, 15),
            temp_max_c=32.5,
            temp_min_c=18.2,
            precipitation_mm=0.0,
        )
        assert r.temp_max_c == 32.5
        assert r.precipitation_mm == 0.0

    def test_empty_string_becomes_none(self):
        r = InmetDailyRecord(
            station_code="A001",
            measure_date=date(2024, 6, 15),
            temp_max_c="",
            temp_min_c="-9999",
            precipitation_mm=-9999,
        )
        assert r.temp_max_c is None
        assert r.temp_min_c is None
        assert r.precipitation_mm is None

    def test_sentinel_minus_9999_becomes_none(self):
        r = InmetDailyRecord(
            station_code="A002",
            measure_date=date(2024, 7, 1),
            humidity_pct=-9999.0,
            wind_speed_ms=-9999,
        )
        assert r.humidity_pct is None
        assert r.wind_speed_ms is None


class TestInmetConnector:
    @patch("ingestion.inmet.connector.requests.get")
    def test_fetch_stations_filters_cerrado(self, mock_get: MagicMock):
        mock_get.return_value.json.return_value = [
            {"CD_ESTACAO": "A001", "DC_NOME": "Brasília", "SG_ESTADO": "DF",
             "VL_LATITUDE": -15.79, "VL_LONGITUDE": -47.93, "VL_ALTITUDE": 1160},
            {"CD_ESTACAO": "B001", "DC_NOME": "Manaus", "SG_ESTADO": "AM",
             "VL_LATITUDE": -3.1, "VL_LONGITUDE": -60.0, "VL_ALTITUDE": 72},
        ]
        mock_get.return_value.raise_for_status = MagicMock()

        from ingestion.inmet.connector import fetch_stations
        stations = fetch_stations()

        assert len(stations) == 1
        assert stations[0].station_code == "A001"
        assert stations[0].state == "DF"

    @patch("ingestion.inmet.connector.requests.get")
    def test_fetch_daily_observations(self, mock_get: MagicMock):
        mock_get.return_value.json.return_value = [
            {"DT_MEDICAO": "2024-06-15", "TEM_MAX": "32.5", "TEM_MIN": "18.0",
             "TEM_INS": "25.0", "CHUVA": "5.2", "UMD_MED": "68", "VEN_VEL": "2.1"},
        ]
        mock_get.return_value.raise_for_status = MagicMock()

        station = InmetStationRecord(
            station_code="A001", station_name="Test", state="GO",
            latitude=-16.0, longitude=-49.0,
        )
        from ingestion.inmet.connector import fetch_daily_observations
        records = fetch_daily_observations(
            station, date(2024, 6, 15), date(2024, 6, 15)
        )

        assert len(records) == 1
        assert records[0].temp_max_c == 32.5
        assert records[0].precipitation_mm == 5.2

    @patch("ingestion.inmet.connector.requests.get")
    def test_fetch_observations_handles_error(self, mock_get: MagicMock):
        import requests
        mock_get.side_effect = requests.RequestException("timeout")

        station = InmetStationRecord(
            station_code="A999", station_name="Bad", state="GO",
            latitude=-16.0, longitude=-49.0,
        )
        from ingestion.inmet.connector import fetch_daily_observations
        records = fetch_daily_observations(
            station, date(2024, 6, 1), date(2024, 6, 15)
        )
        assert records == []
