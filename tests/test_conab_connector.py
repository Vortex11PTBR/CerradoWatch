"""Testes para o conector CONAB."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ingestion.conab.schema import ConabPriceRecord


class TestConabSchema:
    def test_valid_record(self):
        r = ConabPriceRecord(
            product="soja",
            reference_date=date(2024, 1, 1),
            state="GO",
            price_per_sack=145.20,
        )
        assert r.product == "soja"
        assert r.state == "GO"
        assert r.price_per_sack == 145.20

    def test_product_normalized(self):
        r = ConabPriceRecord(
            product="Soja Grão",
            reference_date=date(2024, 1, 1),
            state="mt",
            price_per_sack=143.0,
        )
        assert r.product == "soja_grão"
        assert r.state == "MT"

    def test_zero_price_becomes_none(self):
        r = ConabPriceRecord(
            product="milho",
            reference_date=date(2024, 3, 1),
            state="GO",
            price_per_sack=0,
        )
        assert r.price_per_sack is None

    def test_price_with_comma(self):
        r = ConabPriceRecord(
            product="milho",
            reference_date=date(2024, 3, 1),
            state="MS",
            price_per_sack="58,30",  # type: ignore[arg-type]
        )
        assert r.price_per_sack == 58.30


class TestConabConnector:
    def test_fallback_records_soja(self):
        from ingestion.conab.connector import _fallback_records
        records = _fallback_records("soja")
        assert len(records) > 0
        assert all(r.product == "soja" for r in records)
        assert all(r.state in {"GO", "MT", "MS"} for r in records)

    def test_fallback_records_milho(self):
        from ingestion.conab.connector import _fallback_records
        records = _fallback_records("milho")
        assert len(records) > 0
        assert all(r.product == "milho" for r in records)

    def test_fallback_algodao_retorna_vazio(self):
        """algodão não tem dados de fallback pré-definidos."""
        from ingestion.conab.connector import _fallback_records
        records = _fallback_records("algodao")
        assert records == []

    def test_fallback_soja_todos_estados_cerrado(self):
        from ingestion.conab.connector import _fallback_records, CERRADO_STATES
        records = _fallback_records("soja")
        for r in records:
            assert r.state in CERRADO_STATES

    @patch("ingestion.conab.connector.requests.get")
    def test_fetch_prices_falls_back_on_error(self, mock_get: MagicMock):
        import requests
        mock_get.side_effect = requests.RequestException("API indisponível")

        from ingestion.conab.connector import fetch_prices
        records = fetch_prices("soja")

        # Deve retornar dados de fallback, não lançar exceção
        assert len(records) > 0
        assert all(r.product == "soja" for r in records)

    @patch("ingestion.conab.connector.requests.get")
    def test_fetch_prices_falls_back_on_empty_xlsx(self, mock_get: MagicMock):
        mock_get.return_value.content = b""  # conteúdo vazio
        mock_get.return_value.raise_for_status = MagicMock()

        from ingestion.conab.connector import fetch_prices
        records = fetch_prices("milho")

        # XLSX vazio → fallback
        assert len(records) > 0
