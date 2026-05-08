"""
Alertas por e-mail — dispara quando o volume de queimadas supera threshold.

Usa SMTP padrão (Gmail App Password recomendado).
Configurado via variáveis de ambiente (SMTP_HOST, SMTP_USER, etc.)
"""
from __future__ import annotations

import smtplib
from dataclasses import dataclass
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger

from ingestion.config import settings


@dataclass
class FireAlertPayload:
    """Dados usados para montar o e-mail de alerta."""
    week_start: date
    week_end: date
    total_fires: int
    threshold: int
    top_state: str
    max_frp_mw: float
    high_confidence_count: int


def _build_html(payload: FireAlertPayload) -> str:
    pct_over = round((payload.total_fires / payload.threshold - 1) * 100, 1)
    return f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:auto;padding:24px">
      <div style="background:#ff4500;color:white;padding:16px 24px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">🔥 Alerta CerradoWatch — Queimadas Acima do Limite</h2>
      </div>
      <div style="border:1px solid #e5e5e5;border-top:none;padding:24px;border-radius:0 0 8px 8px">
        <p>O monitoramento semanal detectou <strong>{payload.total_fires:,} focos de queimada</strong>
        no Cerrado entre <strong>{payload.week_start}</strong> e <strong>{payload.week_end}</strong>.</p>

        <table style="width:100%;border-collapse:collapse;margin:16px 0">
          <tr style="background:#fff3e0">
            <td style="padding:12px;border:1px solid #ffe0b2"><strong>Focos detectados</strong></td>
            <td style="padding:12px;border:1px solid #ffe0b2;color:#e65100">
              <strong>{payload.total_fires:,}</strong>
            </td>
          </tr>
          <tr>
            <td style="padding:12px;border:1px solid #e0e0e0">Limite configurado</td>
            <td style="padding:12px;border:1px solid #e0e0e0">{payload.threshold:,}</td>
          </tr>
          <tr style="background:#fce4ec">
            <td style="padding:12px;border:1px solid #f8bbd0">Acima do limite</td>
            <td style="padding:12px;border:1px solid #f8bbd0;color:#c62828">
              <strong>+{pct_over}%</strong>
            </td>
          </tr>
          <tr>
            <td style="padding:12px;border:1px solid #e0e0e0">Estado com mais focos</td>
            <td style="padding:12px;border:1px solid #e0e0e0">{payload.top_state}</td>
          </tr>
          <tr>
            <td style="padding:12px;border:1px solid #e0e0e0">Maior FRP detectado</td>
            <td style="padding:12px;border:1px solid #e0e0e0">{payload.max_frp_mw:.1f} MW</td>
          </tr>
          <tr>
            <td style="padding:12px;border:1px solid #e0e0e0">Focos de alta confiança</td>
            <td style="padding:12px;border:1px solid #e0e0e0">{payload.high_confidence_count:,}</td>
          </tr>
        </table>

        <p style="font-size:12px;color:#888">
          Dados: NASA FIRMS / VIIRS-SNPP NRT · CerradoWatch v1.0
        </p>
      </div>
    </body></html>
    """


def send_fire_alert(payload: FireAlertPayload) -> bool:
    """
    Envia e-mail de alerta. Retorna True se enviado com sucesso.
    Falha silenciosa com log de erro (não bloqueia o pipeline).
    """
    if not settings.smtp_user or not settings.alert_email_to:
        logger.warning("Alerta de e-mail não configurado (SMTP_USER ou ALERT_EMAIL_TO ausentes).")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"🔥 CerradoWatch: {payload.total_fires:,} focos de queimada "
        f"({payload.week_start} a {payload.week_end})"
    )
    msg["From"] = settings.smtp_user
    msg["To"] = settings.alert_email_to

    plain = (
        f"CerradoWatch - Alerta de Queimadas\n"
        f"Período: {payload.week_start} a {payload.week_end}\n"
        f"Focos detectados: {payload.total_fires:,} (limite: {payload.threshold:,})\n"
        f"Estado com mais focos: {payload.top_state}\n"
        f"Maior FRP: {payload.max_frp_mw:.1f} MW\n"
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(_build_html(payload), "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, settings.alert_email_to, msg.as_string())
        logger.info(f"Alerta enviado para {settings.alert_email_to}")
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar alerta: {e}")
        return False
