"""SQLAlchemy engine/session plumbing shared by all services.

Default development driver is SQLite (zero-setup). Production uses PostgreSQL
via ``postgresql+psycopg://`` connection strings - no code changes required.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from worldview.config import Settings, get_settings

_ENGINES: dict[str, Engine] = {}
_SESSION_FACTORIES: dict[str, sessionmaker[Session]] = {}


class Base(DeclarativeBase):
    """Declarative base for all WorldView ORM models."""


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def get_engine(database_url: str | None = None, settings: Settings | None = None) -> Engine:
    """Return a lazily-created, cached SQLAlchemy engine.

    PostgreSQL engines use a bounded connection pool (size/overflow/timeout) so
    a database outage backpressures instead of exhausting file descriptors.
    SQLite engines use a single thread-safe connection (the dev default).
    """
    settings = settings or get_settings()
    url = database_url or settings.database_url
    if url not in _ENGINES:
        if url.startswith("sqlite"):
            _ensure_sqlite_dir(url)
            _ENGINES[url] = create_engine(url, connect_args=_connect_args(url), pool_pre_ping=True)
        else:
            _ENGINES[url] = create_engine(
                url,
                connect_args=_connect_args(url),
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout_seconds,
                pool_recycle=settings.db_pool_recycle_seconds,
                pool_pre_ping=settings.db_pool_pre_ping,
            )
    return _ENGINES[url]


def _ensure_sqlite_dir(database_url: str) -> None:
    """Create the parent directory for a file-backed SQLite database."""
    path = database_url.replace("sqlite:///", "", 1)
    if path == ":memory:":
        return
    parent = path.rsplit("/", 1)[0] if "/" in path else path.rsplit("\\", 1)[0]
    if parent and parent != path:
        Path(parent).mkdir(parents=True, exist_ok=True)


def get_session_factory(
    database_url: str | None = None, settings: Settings | None = None
) -> sessionmaker[Session]:
    """Return a cached sessionmaker bound to the engine for ``database_url``."""
    settings = settings or get_settings()
    url = database_url or settings.database_url
    if url not in _SESSION_FACTORIES:
        _SESSION_FACTORIES[url] = sessionmaker(
            bind=get_engine(url, settings), expire_on_commit=False
        )
    return _SESSION_FACTORIES[url]


def init_db(database_url: str | None = None, settings: Settings | None = None) -> None:
    """Initialise the schema for the given engine.

    Dev convenience: ``create_all`` on an empty database.
    Production safety: do NOT create tables implicitly - require the schema to
    exist (created by Alembic migrations, ``make migrate``) and fail loudly if
    it is missing so deployments can never drift.
    """
    settings = settings or get_settings()
    engine = get_engine(database_url, settings)
    if settings.env == "prod":
        _assert_schema_present(engine, settings.service_name)
    else:
        Base.metadata.create_all(engine)


def _assert_schema_present(engine, service_name: str) -> None:
    from sqlalchemy import inspect

    inspector = inspect(engine)
    missing = [
        table.name for table in Base.metadata.sorted_tables if not inspector.has_table(table.name)
    ]
    if missing:
        raise RuntimeError(
            f"{service_name}: schema missing tables {missing} - "
            "run `make migrate` (Alembic) before booting in prod"
        )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a session and rolling back on error.

    Parameterless on purpose: any Pydantic-typed parameters would be
    introspected by FastAPI as additional body/query dependencies and corrupt
    the request schema.
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
