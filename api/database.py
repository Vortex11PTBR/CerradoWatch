"""Engine compartilhado para a FastAPI — reutiliza settings do projeto."""
from functools import lru_cache

from sqlalchemy import create_engine

from ingestion.config import settings


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(
        settings.db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
