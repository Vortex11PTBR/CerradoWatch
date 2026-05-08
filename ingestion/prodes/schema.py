"""Modelos Pydantic para dados do PRODES (TerraBrasilis)."""
from pydantic import BaseModel, Field, field_validator


class ProdesRecord(BaseModel):
    """
    Incremento de desmatamento detectado pelo PRODES no Cerrado.
    Fonte: TerraBrasilis WFS API — prodes-cerrado-nb:yearly_deforestation_biome
    """
    year: int = Field(..., ge=2000, le=2100)
    state: str = Field(..., description="Sigla do estado (ex: GO, MT)")
    municipality: str = Field(default="", description="Nome do município")
    area_km2: float = Field(..., ge=0, description="Área desmatada em km²")
    biome: str = Field(default="Cerrado")
    class_name: str = Field(default="d", description="Classe PRODES (d=deforestation)")

    @field_validator("state", mode="before")
    @classmethod
    def normalize_state(cls, v: object) -> str:
        return str(v).strip().upper()

    @field_validator("year", mode="before")
    @classmethod
    def parse_year(cls, v: object) -> int:
        return int(str(v).strip())
