"""Repeatable in-process warm-path benchmark for the Glance highlights endpoint."""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed import SYNTHETIC_PATIENT_ID, seed_demo_data  # noqa: E402


HEADERS = {
    "X-User-Id": "clinician-demo-001",
    "X-Role": "clinician",
    "X-Clinic-Id": "clinic-demo-001",
}


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def benchmark(requests: int, warmups: int) -> dict[str, object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with session_factory() as db:
        seed_demo_data(db)

    def override_get_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    path = f"/patients/{SYNTHETIC_PATIENT_ID}/highlights"
    latencies_ms: list[float] = []
    try:
        with TestClient(app, headers=HEADERS) as client:
            for _ in range(warmups):
                response = client.get(path)
                response.raise_for_status()
            for _ in range(requests):
                started = perf_counter_ns()
                response = client.get(path)
                elapsed_ms = (perf_counter_ns() - started) / 1_000_000
                response.raise_for_status()
                latencies_ms.append(elapsed_ms)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    return {
        "endpoint": path,
        "requests": requests,
        "warmups": warmups,
        "median_ms": round(statistics.median(latencies_ms), 3),
        "p95_ms": round(percentile_nearest_rank(latencies_ms, 0.95), 3),
        "min_ms": round(min(latencies_ms), 3),
        "max_ms": round(max(latencies_ms), 3),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "fastapi": version("fastapi"),
            "sqlalchemy": version("sqlalchemy"),
            "database": "SQLite in-memory / StaticPool",
            "transport": "FastAPI TestClient in-process (no network or browser rendering)",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--warmups", type=int, default=20)
    args = parser.parse_args()
    if args.requests < 1 or args.warmups < 0:
        parser.error("--requests must be positive and --warmups cannot be negative")
    print(json.dumps(benchmark(args.requests, args.warmups), indent=2))


if __name__ == "__main__":
    main()
