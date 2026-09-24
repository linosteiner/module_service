from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # Either a complete URL (local development, see .env.example) or the individual parts
    # below (Kubernetes). The parts exist so the password can come from a Secret on its own:
    # URL.create() escapes it, which a hand-assembled DATABASE_URL would not.
    database_url: str | None = None
    db_host: str | None = None
    db_port: int = 3306
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None

    # TLS to MySQL is on unless explicitly disabled; DigitalOcean's managed MySQL refuses
    # unencrypted connections anyway. With a CA file the server certificate is verified
    # against it, and mysql_ssl_verify_hostname additionally checks the host name.
    mysql_ssl_disabled: bool = False
    mysql_ssl_ca: str | None = None
    mysql_ssl_verify_hostname: bool = True

    @model_validator(mode="after")
    def _require_database(self) -> "Settings":
        if self.database_url is None and not (self.db_host and self.db_name and self.db_user):
            raise ValueError("set DATABASE_URL, or DB_HOST, DB_NAME and DB_USER")
        return self

    @property
    def sqlalchemy_url(self) -> URL:
        if self.database_url is not None:
            return make_url(self.database_url)
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
