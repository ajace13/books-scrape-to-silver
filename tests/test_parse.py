"""Tests for the catalogue parser, run against the saved tests/fixtures/page-1.html. No network."""
from pathlib import Path

import pytest
import requests

from books_pipeline.parse import parse_page

PAGE_1 = Path(__file__).parent / "fixtures" / "page-1.html"


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any call to requests.get fail the test."""
    def forbidden_get(*args, **kwargs):
        raise AssertionError(f"network request attempted: {args} {kwargs}")
    monkeypatch.setattr(requests, "get", forbidden_get)


@pytest.fixture
def books() -> list[dict]:
    """Books parsed from the saved first catalogue page."""
    return parse_page(PAGE_1.read_bytes().decode("utf-8"))


def test_page_has_20_books(books: list[dict]) -> None:
    assert len(books) == 20


def test_first_title(books: list[dict]) -> None:
    assert books[0]["title"] == "A Light in the Attic"


def test_every_price_starts_with_pound_sign(books: list[dict]) -> None:
    prices_without_pound_sign = [book["price"] for book in books if not book["price"].startswith("£")]
    assert prices_without_pound_sign == []
