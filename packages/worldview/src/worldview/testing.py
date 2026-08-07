"""Test helpers shared by all service test suites.

Tests run against PostgreSQL when ``WORLDVIEW_TEST_DATABASE_URL`` is set
(CI does this), otherwise they fall back to a per-test SQLite file so local
development stays zero-setup.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def test_database_url(tmp_path: Path) -> str:
    """Return the Postgres URL from CI/env or a per-test SQLite file."""
    override = os.environ.get("WORLDVIEW_TEST_DATABASE_URL")
    if override:
        return override
    return f"sqlite:///{tmp_path / 'test.db'}"


def truncate_all(database_url: str) -> None:
    """Empty every application table, isolating tests that share a database."""
    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = [t for t in inspector.get_table_names() if not t.startswith("alembic_")]
    if not tables:
        return
    with engine.connect() as conn:
        if database_url.startswith("sqlite"):
            for table in tables:
                conn.execute(text(f'DELETE FROM "{table}"'))  # nosec B608
        else:
            conn.execute(
                text(
                    "TRUNCATE TABLE "
                    + ", ".join(f'"{t}"' for t in tables)
                    + " RESTART IDENTITY CASCADE"
                )
            )
        conn.commit()
