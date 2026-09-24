"""Applies schema.sql to the configured database: `python -m app.migrate`.

Runs as the Deployment's init container before every pod start. Every statement in
schema.sql is idempotent (CREATE TABLE IF NOT EXISTS, INSERT IGNORE), so repeated and even
concurrent runs by several starting replicas leave the same result.
"""

import logging
import sys
from pathlib import Path

from sqlalchemy import text

from app.config import get_settings
from app.database import engine

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schema.sql"

logger = logging.getLogger("app.migrate")


def statements(sql: str) -> list[str]:
    # schema.sql contains no semicolons inside literals, so splitting on them is enough.
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def migrate() -> int:
    parts = statements(SCHEMA_FILE.read_text(encoding="utf-8"))
    with engine.begin() as connection:
        for statement in parts:
            connection.execute(text(statement))
    return len(parts)


if __name__ == "__main__":
    logging.basicConfig(
        level=get_settings().log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    try:
        count = migrate()
    except Exception:
        logger.exception("schema migration failed")
        sys.exit(1)
    logger.info("applied %d statements from %s", count, SCHEMA_FILE.name)
