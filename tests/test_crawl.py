"""Tests for the catalogue walk and completeness checks, run against saved pages. No network."""
import shutil
from pathlib import Path

import pandas as pd

from books_pipeline.config import DataPaths
from books_pipeline.crawl import book_path, check_books, walk_catalogue


def complete_books(row_count: int) -> pd.DataFrame:
    return pd.DataFrame({
        "title": [f"Book {i}" for i in range(row_count)],
        "url": [f"http://books.toscrape.com/catalogue/book-{i}_{i}/index.html" for i in range(row_count)],
        "category": pd.Series(["Poetry"] * row_count, dtype="string"),
        "upc": pd.Series([f"upc{i}" for i in range(row_count)], dtype="string"),
    })


def test_walk_reads_saved_first_page(fixtures_dir: Path, tmp_path: Path) -> None:
    paths = DataPaths(tmp_path)
    paths.raw.mkdir(parents=True)
    shutil.copy(fixtures_dir / "page-1.html", paths.raw / "page-1.html")
    books = walk_catalogue(paths, max_pages=1)
    assert books.shape == (20, 6)
    assert set(books["page"]) == {1}


def test_book_path_uses_url_folder(tmp_path: Path) -> None:
    url = "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert book_path(url, tmp_path) == tmp_path / "a-light-in-the-attic_1000.html"


def test_complete_table_has_no_problems() -> None:
    assert check_books(complete_books(3), expected_rows=3) == []


def test_wrong_row_count_is_reported() -> None:
    problems = check_books(complete_books(2), expected_rows=3)
    assert "expected 3 rows, got 2" in problems


def test_blank_upc_is_reported() -> None:
    books = complete_books(3)
    books.loc[1, "upc"] = pd.NA
    assert any("blank upc" in problem for problem in check_books(books, expected_rows=3))


def test_repeated_upc_is_reported() -> None:
    books = complete_books(3)
    books.loc[2, "upc"] = "upc0"
    assert any("share a upc" in problem for problem in check_books(books, expected_rows=3))
