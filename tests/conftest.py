"""Shared fixtures: temporary data file, fixed clock and an app wired to both."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.clock import FixedClock, get_clock
from app.config import PROJECT_ROOT, Settings
from app.main import create_app
from app.repositories.json_store import JsonStore

TODAY = date(2026, 10, 23)


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    return tmp_path / "budget.json"


@pytest.fixture
def store(data_file: Path) -> JsonStore:
    s = JsonStore(data_file)
    s.initialize()
    return s


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(TODAY)


@pytest.fixture
def client(data_file: Path, clock: FixedClock) -> Iterator[TestClient]:
    """API client on a temporary data file with "today" fixed to 2026-10-23."""
    app = create_app(Settings(data_file=data_file, static_dir=PROJECT_ROOT / "static"))
    app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app) as test_client:
        yield test_client
