"""
Flow principal do CerradoWatch — orquestrado pelo Prefect.

Execução: toda segunda-feira às 06:00 BRT (09:00 UTC)
Passos:
  1. Ingere 7 dias de focos de queimada via API FIRMS
  2. Carrega no PostgreSQL (upsert idempotente)
  3. Verifica se volume semanal supera threshold
  4. Se sim, envia alerta por e-mail
  5. Registra resultado em raw.pipeline_runs

Para rodar manualmente:
  python -m orchestration.weekly_fires_flow

Para deployar no Prefect Cloud:
  prefect deploy orchestration/weekly_fires_flow.py:cerradowatch_weekly
"""
from __future__ import annotations

from datetime import date, timedelta

from loguru import logger
from prefect import flow, task
from prefect.schedules import CronSchedule
from sqlalchemy import func, select, text

from ingestion.config import settings
from ingestion.database import SessionLocal, engine
from ingestion.firms.connector import ensure_table, fetch_fires, upsert_fires
from ingestion.firms.models import FirmsFireEvent
from ingestion.firms.schema import FirmsFireRecord
from orchestration.alerts import FireAlertPayload, send_fire_alert


# ---------------------------------------------------------------------------
# Tasks individuais (cada uma rastreada separadamente no Prefect UI)
# ---------------------------------------------------------------------------

@task(name="fetch-firms-data", retries=3, retry_delay_seconds=60)
def task_fetch_fires(days: int = 7) -> list[FirmsFireRecord]:
    """Busca focos de queimada na API FIRMS com retry automático."""
    return fetch_fires(days=days)


@task(name="load-to-postgres")
def task_load_fires(records: list[FirmsFireRecord]) -> int:
    """Carrega registros no raw.firms_fire_events e retorna total inserido."""
    ensure_table()
    return upsert_fires(records)


@task(name="count-weekly-fires")
def task_count_weekly(days: int = 7) -> dict[str, object]:
    """
    Conta focos da última semana no banco e calcula estatísticas para o alerta.
    Retorna dict com métricas prontas para o payload de alerta.
    """
    week_start = date.today() - timedelta(days=days)
    week_end = date.today()

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

    return {
        "total_fires": total,
        "max_frp_mw": float(max_frp),
        "high_confidence_count": high_conf,
        "week_start": week_start,
        "week_end": week_end,
        "top_state": "Goiás",  # será calculado na Fase 5 com dados geoespaciais
    }


@task(name="send-alert-if-needed")
def task_alert_if_threshold(stats: dict[str, object]) -> bool:
    """Dispara alerta por e-mail se volume supera threshold configurado."""
    total = int(stats["total_fires"])  # type: ignore[arg-type]
    threshold = settings.firms_alert_threshold

    if total <= threshold:
        logger.info(f"Focos ({total:,}) abaixo do limite ({threshold:,}). Sem alerta.")
        return False

    logger.warning(f"🔥 Threshold atingido: {total:,} focos (limite: {threshold:,})")
    payload = FireAlertPayload(
        week_start=stats["week_start"],  # type: ignore[arg-type]
        week_end=stats["week_end"],  # type: ignore[arg-type]
        total_fires=total,
        threshold=threshold,
        top_state=str(stats["top_state"]),
        max_frp_mw=float(stats["max_frp_mw"]),  # type: ignore[arg-type]
        high_confidence_count=int(stats["high_confidence_count"]),  # type: ignore[arg-type]
    )
    return send_fire_alert(payload)


@task(name="log-pipeline-run")
def task_log_run(source: str, records_loaded: int, status: str = "success") -> None:
    """Registra o resultado da execução na tabela raw.pipeline_runs."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO raw.pipeline_runs (source, finished_at, status, records_loaded)
                VALUES (:source, NOW(), :status, :records)
            """),
            {"source": source, "status": status, "records": records_loaded},
        )
    logger.info(f"Pipeline run registrado: {source} | {records_loaded} registros | {status}")


# ---------------------------------------------------------------------------
# Flow principal
# ---------------------------------------------------------------------------

@flow(
    name="cerradowatch-weekly",
    description="Pipeline semanal de queimadas do Cerrado — FIRMS/VIIRS",
    log_prints=True,
)
def cerradowatch_weekly(days: int = 7) -> dict[str, object]:
    """
    Execução completa do pipeline semanal de queimadas.

    Args:
        days: Janela de tempo em dias para buscar dados (padrão: 7)

    Returns:
        Dict com métricas da execução para logging no Prefect UI.
    """
    logger.info(f"Iniciando pipeline CerradoWatch — janela de {days} dias")

    records = task_fetch_fires(days=days)
    inserted = task_load_fires(records)
    stats = task_count_weekly(days=days)
    alert_sent = task_alert_if_threshold(stats)
    task_log_run(source="firms", records_loaded=inserted)

    result = {
        "fetched": len(records),
        "inserted": inserted,
        "total_in_db": stats["total_fires"],
        "alert_sent": alert_sent,
    }
    logger.info(f"Pipeline concluído: {result}")
    return result


# ---------------------------------------------------------------------------
# Entrypoint para execução local
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cerradowatch_weekly()
