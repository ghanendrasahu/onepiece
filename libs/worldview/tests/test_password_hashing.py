"""Password hashing (argon2id + legacy PBKDF2) and connection-pool tests."""

from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from worldview.auth import hash_password, needs_rehash, verify_password
from worldview.config import Settings
from worldview.db import get_engine

_PBKDF2 = (
    "pbkdf2$600000$00112233445566778899aabbccddeeff"
    "$71d5d4a6be63351b74c57ba342053aabdc80a15b709da1c5f86fc44a9b1e7cf2"
)


def test_hash_password_uses_argon2id():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong-password", hashed)


def test_verify_accepts_legacy_pbkdf2():
    assert verify_password("supersecret", _PBKDF2)
    assert not verify_password("not-the-password", _PBKDF2)


def test_verify_rejects_garbage():
    assert not verify_password("anything", "not-a-hash")
    assert not verify_password("anything", "")


def test_needs_rehash_flags_legacy_and_unknown():
    assert needs_rehash(_PBKDF2) is True
    assert needs_rehash("$argon2$v=19$m=65536,t=3,p=4$x$y") is True
    assert needs_rehash("garbage") is True


def test_needs_rehash_false_for_argon2id():
    assert needs_rehash(hash_password("current-profile")) is False


def test_engine_pools_postgres_but_not_sqlite(tmp_path):
    settings = Settings.model_construct(
        env="dev",
        database_url=f"sqlite:///{tmp_path / 't.db'}",
        db_pool_size=4,
        db_max_overflow=8,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=60,
    )
    sqlite_engine: Engine = get_engine(settings=settings)
    assert isinstance(sqlite_engine.pool, QueuePool)
    # SQLite path must ignore the production pool tuning (uses engine defaults).
    assert sqlite_engine.pool._max_overflow == 10  # default, not our 8

    pg_settings = settings.model_copy(update={"database_url": "postgresql+psycopg://u:p@h/db"})
    pg_engine = get_engine(settings=pg_settings)
    assert isinstance(pg_engine.pool, QueuePool)
    assert pg_engine.pool.size() == 4
    assert pg_engine.pool._max_overflow == 8
    assert pg_engine.pool._timeout == 5
    assert pg_engine.pool._recycle == 60
