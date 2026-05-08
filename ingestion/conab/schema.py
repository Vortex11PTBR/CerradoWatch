"""Modelos Pydantic para dados de preços agrícolas da CONAB."""
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


CERRADO_PRODUCTS = Literal[
    "soja",
    "milho",
    "algodao",
    "sorgo",
    "cana_de_acucar",
]


class ConabPriceRecord(BaseModel):
    """
    Preço de produto agrícola publicado pela CONAB.
    Endpoint: https://portaldeinformacoes.conab.gov.br/
    Produtos monitorados: soja, milho, algodão (principais commodities do Cerrado)
    """
    product: str = Field(..., description="Nome do produto (ex: soja, milho)")
    reference_date: date = Field(..., description="Data de referência do preço")
    state: str = Field(..., description="Estado (UF)")
    price_per_sack: Optional[float] = Field(
        None, ge=0, description="Preço por saca (R$/sc 60kg)"
    )
    price_per_ton: Optional[float] = Field(
        None, ge=0, description="Preço por tonelada (R$/t)"
    )
    unit: str = Field(default="R$/sc 60kg")
    source_url: str = Field(default="https://www.conab.gov.br")

    @field_validator("product", mode="before")
    @classmethod
    def normalize_product(cls, v: object) -> str:
        return str(v).strip().lower().replace(" ", "_").replace("-", "_")

    @field_validator("state", mode="before")
    @classmethod
    def normalize_state(cls, v: object) -> str:
        return str(v).strip().upper()

    @field_validator("price_per_sack", "price_per_ton", mode="before")
    @classmethod
    def empty_to_none(cls, v: object) -> object:
        if v in ("", None, "0", 0, 0.0):
            return None
        try:
            return float(str(v).replace(",", "."))
        except (ValueError, TypeError):
            return None
