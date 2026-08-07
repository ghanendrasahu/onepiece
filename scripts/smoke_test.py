"""Live smoke test: boots all four services with uvicorn and exercises the full stack over HTTP."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import time

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = tempfile.mkdtemp() + "/smoke.db"

_seed_spec = importlib.util.spec_from_file_location(
    "seed_catalog", os.path.join(ROOT, "scripts", "seed_catalog.py")
)
if _seed_spec is None:
    raise SystemExit("cannot locate scripts/seed_catalog.py")
_seed_loader = _seed_spec.loader
if _seed_loader is None:
    raise SystemExit("seed_catalog has no loader")
seed_catalog = importlib.util.module_from_spec(_seed_spec)
_seed_loader.exec_module(seed_catalog)

SERVICES = [
    ("identity", 8001),
    ("catalog", 8002),
    ("streaming", 8003),
    ("ai_guide", 8004),
    ("gateway", 8000),
]

BASE = {name: f"http://127.0.0.1:{port}" for name, port in SERVICES}

procs = []
failures = []


def boot():
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{DB}"
    env["JWT_SECRET"] = "smoke-test-secret-key-01234567890123456789"
    for name, port in SERVICES:
        p = subprocess.Popen(  # noqa: S603 - fixed, trusted args
            [
                sys.executable,
                "-m",
                "uvicorn",
                f"worldview_{name}.main:app",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append((name, p))
        print(f"booted {name} pid={p.pid}", flush=True)


def wait_ready(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        all_ok = True
        for name, _port in SERVICES:
            try:
                if httpx.get(f"{BASE[name]}/healthz", timeout=2).status_code != 200:
                    all_ok = False
            except Exception:
                all_ok = False
        if all_ok:
            return True
        time.sleep(0.5)
    return False


def check(service, label, cond, extra=""):
    if cond:
        print(f"  ok  {service}: {label}")
    else:
        failures.append(f"{service}: {label}")
        print(f"FAIL  {service}: {label} {extra}")


def run():
    if not wait_ready():
        print("services did not become ready")
        return 1

    with httpx.Client(timeout=15) as c:
        reg = c.post(
            f"{BASE['identity']}/v1/auth/register",
            json={
                "email": "mira@worldviewvr.com",
                "password": "supersecret1",
                "display_name": "Mira",
            },
        )
        check("identity", "register", reg.status_code == 201)
        token = reg.json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}

        me = c.get(f"{BASE['identity']}/v1/users/me", headers=auth)
        email_ok = me.status_code == 200 and me.json()["email"] == "mira@worldviewvr.com"
        check("identity", "me endpoint", email_ok)

        s = c.post(f"{BASE['streaming']}/v1/streams", json={"tour_id": "tour-tokyo"}, headers=auth)
        check("streaming", "create stream", s.status_code == 201, str(s.json()))
        sid = s.json()["id"]
        c.post(f"{BASE['streaming']}/v1/streams/{sid}/start", headers=auth)
        live = c.get(f"{BASE['streaming']}/v1/streams/live")
        check("streaming", "start + live list", live.status_code == 200 and len(live.json()) == 1)
        ended = c.post(f"{BASE['streaming']}/v1/streams/{sid}/end", headers=auth)
        check("streaming", "end stream", ended.json()["status"] == "ended")
        bad = c.post(f"{BASE['streaming']}/v1/streams/{sid}/start", headers=auth)
        check("streaming", "reject ended->live", bad.status_code == 409)

        seed_catalog.seed(f"sqlite:///{DB}")
        tours = c.get(f"{BASE['catalog']}/v1/tours")
        titles = [t["title_en"] for t in tours.json()["items"]] if tours.status_code == 200 else []
        check(
            "catalog",
            "list tours",
            tours.status_code == 200 and "Tokyo Night Walk" in titles,
        )
        nearby = c.get(
            f"{BASE['catalog']}/v1/explore/nearby",
            params={"lat": 35.66, "lng": 139.70, "radius_km": 10},
        )
        check(
            "catalog",
            "geo nearby",
            nearby.status_code == 200 and len(nearby.json()) == 1,
            str(nearby.json()),
        )

        ask = c.post(
            f"{BASE['ai_guide']}/v1/guide/ask",
            json={
                "tour_id": "tour-tokyo",
                "t": 120,
                "text": "What is that orange tower?",
                "lang": "en",
            },
        )
        check(
            "ai_guide",
            "grounded ask",
            ask.status_code == 200 and "Tokyo Tower" in ask.json()["answer"],
            str(ask.json()),
        )
        # Skytree exists only in the seeded catalog, not in the guide's seed set,
        # so a correct answer proves the guide grounded on live catalog data.
        skytree = c.post(
            f"{BASE['ai_guide']}/v1/guide/ask",
            json={
                "tour_id": "tour-tokyo",
                "t": 300,
                "text": "Tell me about the Skytree",
                "lang": "en",
            },
        )
        check(
            "ai_guide",
            "grounded on live catalog",
            skytree.status_code == 200 and "Skytree" in skytree.json()["answer"],
            str(skytree.json()),
        )
        langs = c.get(f"{BASE['ai_guide']}/v1/guide/languages")
        check(
            "ai_guide", "languages", langs.status_code == 200 and "ja" in langs.json()["languages"]
        )

        me_via_gw = c.get(f"{BASE['gateway']}/api/identity/v1/users/me")
        check("gateway", "route to identity", me_via_gw.status_code == 401)
        tours_via_gw = c.get(f"{BASE['gateway']}/api/catalog/v1/tours")
        check("gateway", "route to catalog", tours_via_gw.status_code == 200)
        rid = tours_via_gw.headers.get("X-Request-ID")
        check("gateway", "request-id header", bool(rid))

    print()
    if failures:
        print(f"{len(failures)} FAILURES: {failures}")
        return 1
    print("ALL SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        boot()
        rc = run()
    finally:
        for _, p in procs:
            p.terminate()
    sys.exit(rc)
