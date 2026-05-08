"""Testes do módulo de alertas — sem SMTP real."""
from datetime import date
from unittest.mock import MagicMock, patch

from orchestration.alerts import FireAlertPayload, _build_html, send_fire_alert


def _make_payload(total: int = 800) -> FireAlertPayload:
    return FireAlertPayload(
        week_start=date(2026, 5, 1),
        week_end=date(2026, 5, 8),
        total_fires=total,
        threshold=500,
        top_state="Goiás",
        max_frp_mw=207.65,
        high_confidence_count=12,
    )


def test_build_html_contem_dados_chave():
    html = _build_html(_make_payload())
    assert "800" in html
    assert "500" in html
    assert "Goiás" in html
    assert "207.7" in html  # 207.65 arredonda para 207.7 com :.1f
    assert "60.0%" in html  # +60% acima do limite


def test_build_html_abaixo_do_limite_nao_acontece():
    """_build_html recebe um payload qualquer — sem validação de threshold aqui."""
    html = _build_html(_make_payload(total=300))
    assert "300" in html


def test_send_alert_sem_config_retorna_false():
    """Se SMTP_USER não configurado, retorna False silenciosamente."""
    with patch("orchestration.alerts.settings") as mock_settings:
        mock_settings.smtp_user = ""
        mock_settings.alert_email_to = "test@test.com"
        result = send_fire_alert(_make_payload())
    assert result is False


def test_send_alert_smtp_sucesso():
    """Simula envio bem-sucedido via SMTP mock."""
    payload = _make_payload()
    mock_server = MagicMock()
    mock_smtp_cls = MagicMock(return_value=__import__("contextlib").nullcontext(mock_server))

    with (
        patch("orchestration.alerts.settings") as mock_settings,
        patch("orchestration.alerts.smtplib.SMTP") as mock_smtp,
    ):
        mock_settings.smtp_user = "sender@gmail.com"
        mock_settings.smtp_password = "apppassword"
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.alert_email_to = "dest@gmail.com"
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = send_fire_alert(payload)

    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once()
    mock_server.sendmail.assert_called_once()


def test_send_alert_smtp_falha_retorna_false():
    """Erro de SMTP não propaga — retorna False com log."""
    with (
        patch("orchestration.alerts.settings") as mock_settings,
        patch("orchestration.alerts.smtplib.SMTP", side_effect=ConnectionRefusedError("refused")),
    ):
        mock_settings.smtp_user = "sender@gmail.com"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.alert_email_to = "dest@gmail.com"

        result = send_fire_alert(_make_payload())

    assert result is False
