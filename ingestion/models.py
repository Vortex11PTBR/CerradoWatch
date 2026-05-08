"""SQLAlchemy ORM — tabelas raw para PRODES, INMET e CONAB."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date, DateTime, Float, Index, Integer,
    String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ingestion.database import Base


class ProdesDeforestation(Base):
    __tablename__ = "prodes_deforestation"
    __table_args__ = (
        UniqueConstraint("year", "state", "municipality", name="uq_prodes_year_state_mun"),
        Index("ix_prodes_year_state", "year", "state"),
        {"schema": "raw"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    municipality: Mapped[str] = mapped_column(String(100), default="")
    area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    biome: Mapped[str] = mapped_column(String(50), default="Cerrado")
    class_name: Mapped[str] = mapped_column(String(10), default="d")
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InmetStation(Base):
    __tablename__ = "inmet_stations"
    __table_args__ = (
        Index("ix_inmet_station_state", "state"),
        {"schema": "raw"},
    )

    station_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    station_name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[Optional[float]] = mapped_column(Float)
    station_type: Mapped[str] = mapped_column(String(1), default="T")
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InmetDailyObservation(Base):
    __tablename__ = "inmet_daily_observations"
    __table_args__ = (
        UniqueConstraint("station_code", "measure_date", name="uq_inmet_station_date"),
        Index("ix_inmet_date", "measure_date"),
        Index("ix_inmet_station_date", "station_code", "measure_date"),
        {"schema": "raw"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_code: Mapped[str] = mapped_column(String(10), nullable=False)
    measure_date: Mapped[date] = mapped_column(Date, nullable=False)
    state: Mapped[str] = mapped_column(String(2), default="")
    temp_max_c: Mapped[Optional[float]] = mapped_column(Float)
    temp_min_c: Mapped[Optional[float]] = mapped_column(Float)
    temp_avg_c: Mapped[Optional[float]] = mapped_column(Float)
    precipitation_mm: Mapped[Optional[float]] = mapped_column(Float)
    humidity_pct: Mapped[Optional[float]] = mapped_column(Float)
    wind_speed_ms: Mapped[Optional[float]] = mapped_column(Float)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ConabAgriculturalPrice(Base):
    __tablename__ = "conab_agricultural_prices"
    __table_args__ = (
        UniqueConstraint(
            "product", "reference_date", "state", name="uq_conab_product_date_state"
        ),
        Index("ix_conab_product_date", "product", "reference_date"),
        {"schema": "raw"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    price_per_sack: Mapped[Optional[float]] = mapped_column(
        Float, comment="R$/sc 60kg"
    )
    price_per_ton: Mapped[Optional[float]] = mapped_column(Float, comment="R$/t")
    unit: Mapped[str] = mapped_column(String(20), default="R$/sc 60kg")
    source_url: Mapped[str] = mapped_column(String(200), default="")
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
