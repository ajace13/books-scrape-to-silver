"""Tests for the HTML parsers, run against saved pages in tests/fixtures. No network."""
from pathlib import Path

import pytest

from books_pipeline.parse import next_url, parse_book, parse_page


def read_fixture(fixtures_dir: Path, name: str) -> str:
    return (fixtures_dir / name).read_bytes().decode("utf-8")


@pytest.fixture
def books(fixtures_dir: Path) -> list[dict]:
    """Books parsed from the saved first catalogue page."""
    return parse_page(read_fixture(fixtures_dir, "page-1.html"))


def test_page_has_20_books(books: list[dict]) -> None:
    assert len(books) == 20


def test_first_title(books: list[dict]) -> None:
    assert books[0]["title"] == "A Light in the Attic"


def test_every_price_starts_with_pound_sign(books: list[dict]) -> None:
    prices_without_pound_sign = [book["price"] for book in books if not book["price"].startswith("£")]
    assert prices_without_pound_sign == []


def test_book_urls_are_absolute(books: list[dict]) -> None:
    assert books[0]["url"] == "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"


def test_next_url_from_first_page(fixtures_dir: Path) -> None:
    html = read_fixture(fixtures_dir, "page-1.html")
    assert next_url(html, "http://books.toscrape.com/catalogue/page-1.html") == "http://books.toscrape.com/catalogue/page-2.html"


def test_last_page_has_no_next_url(fixtures_dir: Path) -> None:
    html = read_fixture(fixtures_dir, "page-50.html")
    assert next_url(html, "http://books.toscrape.com/catalogue/page-50.html") is None


def test_parse_book_reads_category_and_upc(fixtures_dir: Path) -> None:
    details = parse_book(read_fixture(fixtures_dir, "a-light-in-the-attic_1000.html"))
    assert details == {"category": "Poetry", "upc": "a897fe39b1053632"}


def test_parse_book_missing_elements_give_none() -> None:
    assert parse_book("<html><body></body></html>") == {"category": None, "upc": None}
