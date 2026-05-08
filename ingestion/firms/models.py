"""SQLAlchemy ORM — tabela raw.firms_fire_events."""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ingestion.database import Base


class FirmsFireEvent(Base):
    __tablename__ = "firms_fire_events"
    __table_args__ = (
        Index("ix_firms_acq_date", "acq_date"),
        Index("ix_firms_lat_lon", "latitude", "longitude"),
        {"schema": "raw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    bright_ti4: Mapped[float] = mapped_column(Float, nullable=False)
    scan: Mapped[float] = mapped_column(Float, nullable=False)
    track: Mapped[float] = mapped_column(Float, nullable=False)
    acq_date: Mapped[date] = mapped_column(Date, nullable=False)
    acq_time: Mapped[int] = mapped_column(Integer, nullable=False)
    satellite: Mapped[str] = mapped_column(String(10), nullable=False)
    instrument: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[str] = mapped_column(String(1), nullable=False)
    version: Mapped[str] = mapped_column(String(20))
    bright_ti5: Mapped[float] = mapped_column(Float)
    frp: Mapped[float] = mapped_column(Float, nullable=False, comment="Fire Radiative Power (MW)")
    daynight: Mapped[str] = mapped_column(String(1), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
