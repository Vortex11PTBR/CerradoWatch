"""
Runner direto do pipeline — sem dependência do Prefect.
Usado no Dockerfile.pipeline (Render cron) e no GitHub Actions workflow.

Ordem de execução:
  1. Inicializa schemas e tabelas no PostgreSQL
  2. Ingere dados FIRMS (queimadas)
  3. Ingere dados PRODES (desmatamento)
  4. Ingere dados INMET (clima)
  5. Ingere dados CONAB (preços)
  6. Executa `dbt run` para materializar mart tables
  7. Verifica threshold de queimadas e envia alerta se necessário
  8. Registra execução em raw.pipeline_runs
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

from loguru import logger
from sqlalchemy import func, select, text

# ── Resolve DATABASE_URL → variáveis individuais (para dbt e settings) ────────
_db_url = os.environ.get("DATABASE_URL", "")
if _db_url:
    _p = urllib.parse.urlparse(_db_url)
    _qs = urllib.parse.parse_qs(_p.query)
    os.environ.setdefault("POSTGRES_HOST", _p.hostname or "localhost")
    os.environ.setdefault("POSTGRES_PORT", str(_p.port or 5432))
    os.environ.setdefault("POSTGRES_DB", _p.path.lstrip("/"))
    os.environ.setdefault("POSTGRES_USER", _p.username or "")
    os.environ.setdefault("POSTGRES_PASSWORD", _p.password or "")
    os.environ.setdefault("POSTGRES_SSLMODE", _qs.get("sslmode", ["require"])[0])
    logger.info(f"DATABASE_URL resolvida: host={_p.hostname} db={_p.path.lstrip('/')}")

# ── Diretório dbt (relativo ao repo, funciona no Actions e no Docker) ─────────
DBT_DIR = str(Path(__file__).parent.parent / "dbt")

from ingestion.config import settings  # noqa: E402
from ingestion.database import SessionLocal, engine  # noqa: E402
from ingestion.firms.connector import ensure_table, fetch_fires, upsert_fires  # noqa: E402
from ingestion.firms.models import FirmsFireEvent  # noqa: E402
from orchestration.alerts import FireAlertPayload, send_fire_alert  # noqa: E402

def init_db() -> None:
    """Cria schemas raw/staging/mart e todas as tabelas ORM."""
    logger.info("Inicializando banco de dados...")
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS mart"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raw.pipeline_runs (
                id           SERIAL PRIMARY KEY,
                source       VARCHAR(50) NOT NULL,
                started_at   TIMESTAMPTZ DEFAULT NOW(),
                finished_at  TIMESTAMPTZ,
                status       VARCHAR(20) DEFAULT 'running',
                records_loaded INT DEFAULT 0,
                error_msg    TEXT
            )
        """))

    from ingestion.models import (
        ConabAgriculturalPrice, InmetDailyObservation,
        InmetStation, ProdesDeforestation,
    )
    from ingestion.firms.models import FirmsFireEvent
    from ingestion.database import Base

    Base.metadata.create_all(engine)
    logger.info("Banco de dados inicializado.")


def run_dbt() -> bool:
    """Executa dbt run para materializar mart tables."""
    try:
        result = subprocess.run(
            [
                "dbt", "run",
                "--select", "staging mart",
                "--profiles-dir", DBT_DIR,
                "--project-dir", DBT_DIR,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            logger.info("dbt run: ✅ concluído")
            return True
        logger.warning(f"dbt run falhou:\n{result.stderr[-2000:]}")
        return False
    except FileNotFoundError:
        logger.warning("dbt não encontrado — pulando mart layer")
        return False
    except Exception as e:
        logger.warning(f"dbt run ignorado: {e}")
        return False


def log_run(source: str, records: int, status: str = "success", error: str = "") -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO raw.pipeline_runs
                    (source, finished_at, status, records_loaded, error_msg)
                VALUES (:source, NOW(), :status, :records, :error)
            """),
            {"source": source, "status": status, "records": records, "error": error},
        )


def check_and_alert(days: int = 7) -> bool:
    """Verifica threshold e envia alerta se necessário."""
    week_start = date.today() - timedelta(days=days)
    with SessionLocal() as session:
        total = session.execute(
            select(func.count()).where(FirmsFireEvent.acq_date >= week_start)
        ).scalar_one()
        max_frp = session.execute(
            select(func.max(FirmsFireEvent.frp)).where(FirmsFireEvent.acq_date >= week_start)
        ).scalar_one() or 0.0
        high_conf = session.execute(
            select(func.count()).where(
                FirmsFireEvent.acq_date >= week_start,
                FirmsFireEvent.confidence == "h",
            )
        ).scalar_one()

    threshold = settings.firms_alert_threshold
    logger.info(f"Focos na semana: {total:,} | threshold: {threshold:,}")

    if total <= threshold:
        return False

    logger.warning(f"🔥 Alerta! {total:,} focos (limite: {threshold:,})")
    payload = FireAlertPayload(
        week_start=week_start,
        week_end=date.today(),
        total_fires=total,
        threshold=threshold,
        top_state="Mato Grosso",
        max_frp_mw=float(max_frp),
        high_confidence_count=high_conf,
    )
    return send_fire_alert(payload)


def main(days: int = 7) -> int:
    """Pipeline completo. Retorna 0 em sucesso, 1 em falha crítica."""
    errors = 0

    logger.info("=" * 60)
    logger.info("🌿 CerradoWatch — Pipeline Semanal")
    logger.info(f"   Data: {date.today()} | Janela: {days} dias")
    logger.info("=" * 60)

    # 1. Init DB
    try:
        init_db()
    except Exception as e:
        logger.error(f"FATAL: Falha ao inicializar banco: {e}")
        return 1

    # 2. FIRMS
    try:
        ensure_table()
        records = fetch_fires(days=days)
        count = upsert_fires(records)
        log_run("firms", count)
        logger.info(f"FIRMS: {count} registros ✅")
    except Exception as e:
        logger.error(f"FIRMS falhou: {e}")
        log_run("firms", 0, status="error", error=str(e))
        errors += 1

    # 3. PRODES
    try:
        from ingestion.prodes.connector import run as prodes_run
        count = prodes_run()
        log_run("prodes", count)
        logger.info(f"PRODES: {count} registros ✅")
    except Exception as e:
        logger.error(f"PRODES falhou: {e}")
        log_run("prodes", 0, status="error", error=str(e))
        errors += 1

    # 4. INMET (usa 30 dias para garantir dados disponíveis na API)
    try:
        from ingestion.inmet.connector import run as inmet_run
        count = inmet_run(days_back=30)
        log_run("inmet", count)
        logger.info(f"INMET: {count} registros ✅")
    except Exception as e:
        logger.error(f"INMET falhou: {e}")
        log_run("inmet", 0, status="error", error=str(e))
        errors += 1

    # 5. CONAB
    try:
        from ingestion.conab.connector import run as conab_run
        count = conab_run()
        log_run("conab", count)
        logger.info(f"CONAB: {count} registros ✅")
    except Exception as e:
        logger.error(f"CONAB falhou: {e}")
        log_run("conab", 0, status="error", error=str(e))
        errors += 1

    # 6. dbt run
    dbt_ok = run_dbt()
    log_run("dbt", 0, status="success" if dbt_ok else "warning")

    # 7. Alerta
    try:
        check_and_alert(days=days)
    except Exception as e:
        logger.warning(f"Alerta não enviado: {e}")

    logger.info("=" * 60)
    logger.info(f"Pipeline concluído. Erros: {errors}")
    logger.info("=" * 60)

    # Apenas falha crítica (DB) retorna exit 1 — erros de API externa são warnings
    return 0


if __name__ == "__main__":
    sys.exit(main())
