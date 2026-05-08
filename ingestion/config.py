"""Configurações centrais do projeto via variáveis de ambiente."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Banco de dados
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "cerradowatch"
    postgres_user: str = "cerrado_user"
    postgres_password: str

    # FIRMS / INPE
    firms_map_key: str = ""
    firms_alert_threshold: int = 500

    # E-mail
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_to: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore[call-arg]
