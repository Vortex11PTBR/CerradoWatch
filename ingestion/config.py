"""Configurações centrais do projeto via variáveis de ambiente."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # URL completa do banco (prioridade — usada pelo Neon/Render/Railway)
    # Ex: postgresql://user:pass@host/db?sslmode=require
    database_url: str = ""

    # Variáveis individuais (fallback para desenvolvimento local)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "cerradowatch"
    postgres_user: str = "cerrado_user"
    postgres_password: str = Field(default="")

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
    def db_url(self) -> str:
        """Retorna a URL do banco com driver psycopg2."""
        if self.database_url:
            # Neon/Railway/Render fornecem postgresql://, SQLAlchemy precisa do driver
            return self.database_url.replace(
                "postgresql://", "postgresql+psycopg2://", 1
            )
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
