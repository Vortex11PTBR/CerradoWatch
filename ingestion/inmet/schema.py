"""Modelos Pydantic para dados do INMET."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InmetStationRecord(BaseModel):
    """Metadados de uma estação meteorológica do INMET."""
    station_code: str = Field(..., description="Código da estação (ex: A001)")
    station_name: str
    state: str
    latitude: float
    longitude: float
    altitude_m: Optional[float] = None
    station_type: str = Field(default="T", description="T=automatica, M=manual")


class InmetDailyRecord(BaseModel):
    """
    Observação diária de uma estação INMET.
    Endpoint: GET /estacao/diaria/{data_ini}/{data_fim}/{codigo}
    """
    station_code: str
    measure_date: date
    temp_max_c: Optional[float] = Field(None, description="Temperatura máxima (°C)")
    temp_min_c: Optional[float] = Field(None, description="Temperatura mínima (°C)")
    temp_avg_c: Optional[float] = Field(None, description="Temperatura média (°C)")
    precipitation_mm: Optional[float] = Field(None, ge=0, description="Precipitação (mm)")
    humidity_pct: Optional[float] = Field(None, ge=0, le=100)
    wind_speed_ms: Optional[float] = Field(None, ge=0)
    state: str = ""

    @field_validator("temp_max_c", "temp_min_c", "temp_avg_c", "precipitation_mm",
                     "humidity_pct", "wind_speed_ms", mode="before")
    @classmethod
    def empty_to_none(cls, v: object) -> object:
        """API INMET retorna strings vazias ou '-9999' para dados ausentes."""
        if v in ("", None, "-9999", -9999, -9999.0):
            return None
        return v
