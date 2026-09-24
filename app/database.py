import ssl
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def _mysql_ssl_context(settings: Settings) -> ssl.SSLContext:
    if settings.mysql_ssl_ca is None:
        # Encrypted, but the server is not authenticated. Only for setups without a CA file.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    context = ssl.create_default_context(cafile=settings.mysql_ssl_ca)
    context.check_hostname = settings.mysql_ssl_verify_hostname
    # Python 3.13 turned on strict RFC 5280 checks by default, which reject database server
    # certificates without an Authority Key Identifier -- MySQL's own auto-generated ones among
    # them. The chain is still verified against the CA above; only that extension check is off.
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def _connect_args(settings: Settings) -> dict[str, object]:
    backend = settings.sqlalchemy_url.get_backend_name()
    if backend == "mysql":
        if settings.mysql_ssl_disabled:
            return {"ssl_disabled": True}
        return {"ssl": _mysql_ssl_context(settings)}
    if backend == "sqlite":
        return {"check_same_thread": False}
    return {}


settings = get_settings()
engine = create_engine(
    settings.sqlalchemy_url,
    connect_args=_connect_args(settings),
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
