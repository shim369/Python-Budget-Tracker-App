"""Shared fixtures: temporary data file, fixed clock and an app wired to both."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.clock import Clock, FixedClock, get_clock
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


class MovableClock:
    """Clock whose date (or full Clock) can be changed in the middle of a scenario."""

    def __init__(self, today: date) -> None:
        self.inner: Clock = FixedClock(today)

    def set(self, value: date | Clock) -> None:
        self.inner = FixedClock(value) if isinstance(value, date) else value

    def today(self) -> date:
        return self.inner.today()

    def now(self) -> datetime:
        return self.inner.now()


@pytest.fixture
def movable_clock() -> MovableClock:
    return MovableClock(TODAY)


@pytest.fixture
def make_client(data_file: Path, movable_clock: MovableClock) -> Iterator[Callable[..., TestClient]]:
    """Factory so a test can prepare the data file before the app starts (IT-REC)."""
    clients: list[TestClient] = []

    def factory(*, raise_server_exceptions: bool = True) -> TestClient:
        app = create_app(Settings(data_file=data_file, static_dir=PROJECT_ROOT / "static"))
        app.dependency_overrides[get_clock] = lambda: movable_clock
        test_client = TestClient(app, raise_server_exceptions=raise_server_exceptions)
        test_client.__enter__()  # runs the lifespan (store.initialize)
        clients.append(test_client)
        return test_client

    yield factory
    for test_client in clients:
        test_client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    """API client on a temporary data file with "today" fixed to 2026-10-23 (movable)."""
    return make_client()
