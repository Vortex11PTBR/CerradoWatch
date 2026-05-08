"""Modelos Pydantic para validação dos dados FIRMS/VIIRS."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FirmsFireRecord(BaseModel):
    """Representa um foco de queimada detectado pelo satélite VIIRS."""

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    bright_ti4: float = Field(..., description="Temperatura de brilho canal TI4 (Kelvin)")
    scan: float = Field(..., gt=0)
    track: float = Field(..., gt=0)
    acq_date: date = Field(..., description="Data de aquisição da imagem")
    acq_time: int = Field(..., description="Hora de aquisição (HHMM UTC)")
    satellite: str
    instrument: Literal["VIIRS"]
    confidence: Literal["l", "n", "h"] = Field(
        ..., description="Confiança: l=low, n=nominal, h=high"
    )
    version: str
    bright_ti5: float = Field(..., description="Temperatura de brilho canal TI5 (Kelvin)")
    frp: float = Field(..., ge=0, description="Fire Radiative Power (MW)")
    daynight: Literal["D", "N"] = Field(..., description="D=diurno, N=noturno")

    @field_validator("acq_time", mode="before")
    @classmethod
    def parse_acq_time(cls, v: object) -> int:
        return int(v)
