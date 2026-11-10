"""Shared test setup: no test may touch the network, and fixtures live in tests/fixtures."""
from pathlib import Path

import pytest
import requests

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any call to requests.get fail the test."""
    def forbidden_get(*args, **kwargs):
        raise AssertionError(f"network request attempted: {args} {kwargs}")
    monkeypatch.setattr(requests, "get", forbidden_get)


@pytest.fixture
def fixtures_dir() -> Path:
    """Folder of saved HTML pages and API responses."""
    return FIXTURES
