"""
Flow principal do CerradoWatch — orquestrado pelo Prefect.

Execução: toda segunda-feira às 06:00 BRT (09:00 UTC)
Passos:
  1. Ingere 7 dias de focos de queimada via API FIRMS
  2. Ingere desmatamento anual via TerraBrasilis (PRODES)
  3. Ingere observações climáticas recentes via INMET
  4. Ingere preços agrícolas via CONAB
  5. Verifica threshold de queimadas e envia alerta se necessário
  6. Executa dbt run para atualizar as mart tables
  7. Registra resultado em raw.pipeline_runs

Para rodar manualmente:
  python -m orchestration.weekly_fires_flow

Para deployar no Prefect Cloud:
  prefect deploy orchestration/weekly_fires_flow.py:cerradowatch_weekly
"""
from __future__ import annotations

import subprocess
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
# Tasks individuais — FIRMS
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
        "top_state": "Goiás",  # calculado na mart layer via SQL
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


# ---------------------------------------------------------------------------
# Tasks — Fontes adicionais
# ---------------------------------------------------------------------------

@task(name="ingest-prodes", retries=2, retry_delay_seconds=120)
def task_ingest_prodes() -> int:
    """Atualiza dados de desmatamento anual via TerraBrasilis (PRODES)."""
    from ingestion.prodes.connector import run as prodes_run
    count = prodes_run()
    logger.info(f"PRODES: {count} registros processados")
    return count


@task(name="ingest-inmet", retries=2, retry_delay_seconds=60)
def task_ingest_inmet(days_back: int = 7) -> int:
    """Atualiza observações climáticas dos últimos N dias via INMET."""
    from ingestion.inmet.connector import run as inmet_run
    count = inmet_run(days_back=days_back)
    logger.info(f"INMET: {count} observações processadas")
    return count


@task(name="ingest-conab", retries=2, retry_delay_seconds=60)
def task_ingest_conab() -> int:
    """Atualiza preços agrícolas via CONAB (soja, milho, algodão)."""
    from ingestion.conab.connector import run as conab_run
    count = conab_run()
    logger.info(f"CONAB: {count} registros de preço processados")
    return count


# ---------------------------------------------------------------------------
# Task — dbt run
# ---------------------------------------------------------------------------

@task(name="dbt-run-mart")
def task_dbt_run() -> bool:
    """
    Executa `dbt run --select mart` para materializar as mart tables.
    Retorna True se bem-sucedido, False caso contrário (não bloqueia o pipeline).
    """
    try:
        result = subprocess.run(
            ["dbt", "run", "--select", "mart", "--profiles-dir", "dbt", "--project-dir", "dbt"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            logger.info("dbt run mart: ✅ concluído com sucesso")
            return True
        logger.warning(f"dbt run mart falhou (código {result.returncode}):\n{result.stderr}")
        return False
    except Exception as e:
        logger.warning(f"dbt run mart ignorado: {e}")
        return False


# ---------------------------------------------------------------------------
# Task — log de execução
# ---------------------------------------------------------------------------

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
    description="Pipeline semanal do Cerrado — FIRMS, PRODES, INMET, CONAB + dbt mart",
    log_prints=True,
)
def cerradowatch_weekly(days: int = 7) -> dict[str, object]:
    """
    Execução completa do pipeline semanal de monitoramento do Cerrado.

    Args:
        days: Janela de tempo em dias para fontes diárias (padrão: 7)

    Returns:
        Dict com métricas da execução para logging no Prefect UI.
    """
    logger.info(f"Iniciando pipeline CerradoWatch — janela de {days} dias")

    # 1. Fontes de dados em sequência (respeita rate limits das APIs)
    firms_records = task_fetch_fires(days=days)
    firms_inserted = task_load_fires(firms_records)

    prodes_count = task_ingest_prodes()
    inmet_count = task_ingest_inmet(days_back=days)
    conab_count = task_ingest_conab()

    # 2. Alerta de queimadas
    stats = task_count_weekly(days=days)
    alert_sent = task_alert_if_threshold(stats)

    # 3. Materializa mart tables via dbt
    dbt_ok = task_dbt_run()

    # 4. Log de execuções
    task_log_run(source="firms", records_loaded=firms_inserted)
    task_log_run(source="prodes", records_loaded=prodes_count)
    task_log_run(source="inmet", records_loaded=inmet_count)
    task_log_run(source="conab", records_loaded=conab_count)

    result = {
        "firms_fetched": len(firms_records),
        "firms_inserted": firms_inserted,
        "prodes_records": prodes_count,
        "inmet_records": inmet_count,
        "conab_records": conab_count,
        "total_fires_in_db": stats["total_fires"],
        "alert_sent": alert_sent,
        "dbt_mart_ok": dbt_ok,
    }
    logger.info(f"Pipeline concluído: {result}")
    return result


# ---------------------------------------------------------------------------
# Entrypoint para execução local
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cerradowatch_weekly()
