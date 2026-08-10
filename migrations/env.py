"""Alembic migration environment.

The WorldView schema is shared: all services write to one PostgreSQL database,
so a single migration set covers every table. Models are imported here so
``Base.metadata`` is complete before autogenerate/diffing.
"""

import os

# Import every service's models so their tables are registered on the shared metadata.
import worldview_catalog.models  # noqa: F401
import worldview_identity.models  # noqa: F401
import worldview_moderation.models  # noqa: F401
import worldview_payments.models  # noqa: F401
import worldview_streaming.models  # noqa: F401
from alembic import context
from sqlalchemy import create_engine
from worldview.db import Base

config = context.config

target_metadata = Base.metadata


def get_url() -> str:
    return os.environ.get("DATABASE_URL") or "sqlite:///./data/worldview.db"


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url())
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
