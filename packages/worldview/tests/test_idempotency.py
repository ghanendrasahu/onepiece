"""Idempotency store + middleware replay tests."""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel
from worldview.idempotency import (
    IdempotencyHeaderMiddleware,
    MemoryIdempotencyStore,
    RedisIdempotency,
    build_idempotency_store,
    idempotency_required,
)


class TipIn(BaseModel):
    amount: int


def _app(store=None):
    app = FastAPI()

    @app.post("/tips")
    async def create_tip(payload: TipIn, key: str = idempotency_required()):
        return {"echo": key}

    app.add_middleware(IdempotencyHeaderMiddleware, store=store)
    return app


def test_repeated_key_replays_response():
    client = TestClient(_app(MemoryIdempotencyStore()))
    headers = {"Idempotency-Key": "same-key-00001"}
    first = client.post("/tips", json={"amount": 10}, headers=headers)
    second = client.post("/tips", json={"amount": 10}, headers=headers)
    assert first.status_code == 200
    assert first.json() == second.json()
    assert second.headers["X-Idempotent-Replay"] == "true"


def test_missing_key_rejected():
    client = TestClient(_app(MemoryIdempotencyStore()))
    assert client.post("/tips", json={"amount": 10}).status_code == 400


_app_no_requirement = FastAPI()
_app_no_requirement.add_middleware(IdempotencyHeaderMiddleware)


@_app_no_requirement.post("/plain")
async def plain(req: Request):
    return {"ok": True}


def test_without_key_normal_responses():
    client = TestClient(_app_no_requirement)
    a = client.post("/plain")
    b = client.post("/plain")
    assert a.status_code == 200
    assert "X-Idempotent-Replay" not in b.headers


def test_store_factory_returns_expected_types():
    assert isinstance(build_idempotency_store(None), MemoryIdempotencyStore)
    assert isinstance(build_idempotency_store("redis://localhost:6379/0"), RedisIdempotency)
