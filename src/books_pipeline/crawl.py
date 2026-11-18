"""Walk the catalogue, visit each book's own page, and check the result is complete."""
import logging
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import pandas as pd

from books_pipeline.config import MAX_CONSECUTIVE_DOWNLOAD_FAILURES, START_URL, DataPaths
from books_pipeline.fetch import load_html
from books_pipeline.parse import next_url, parse_book, parse_page

logger = logging.getLogger(__name__)


def book_path(book_url: str, books_dir: Path) -> Path:
    """Where one book's own page is saved, named after its URL folder (e.g. a-light-in-the-attic_1000)."""
    slug = PurePosixPath(urlparse(book_url).path).parent.name
    return books_dir / f"{slug}.html"


def walk_catalogue(paths: DataPaths, max_pages: int, start_url: str = START_URL) -> pd.DataFrame:
    """Follow 'next' from start_url for up to max_pages pages, one row per book."""
    paths.raw.mkdir(parents=True, exist_ok=True)
    rows = []
    url = start_url
    page_number = 0
    while url and page_number < max_pages:
        page_number += 1
        html = load_html(url, paths.raw / f"page-{page_number}.html")
        if html is None:
            logger.error("stopped at page %d: %s could not be fetched", page_number, url)
            break
        page_rows = parse_page(html)
        for row in page_rows:
            row["page"] = page_number
        rows.extend(page_rows)
        logger.info("page %d: %d books", page_number, len(page_rows))
        url = next_url(html, url)
    return pd.DataFrame(rows)


def add_book_details(books: pd.DataFrame, paths: DataPaths) -> pd.DataFrame:
    """Add category and upc from each book's own page. Both stay missing for a book whose page fails."""
    paths.books.mkdir(parents=True, exist_ok=True)
    details = {}
    download_failures = []
    parse_failures = []
    consecutive_download_failures = 0
    for url in books["url"].unique():
        html = load_html(url, book_path(url, paths.books))
        if html is None:
            download_failures.append(url)
            consecutive_download_failures += 1
            if consecutive_download_failures >= MAX_CONSECUTIVE_DOWNLOAD_FAILURES:
                logger.error("stopping early: %d download failures in a row", consecutive_download_failures)
                break
            continue
        consecutive_download_failures = 0
        details[url] = parse_book(html)
        if not details[url]["category"] or not details[url]["upc"]:
            parse_failures.append(url)
            logger.warning(
                "parse failure: %s gave category=%r upc=%r; review the parser, a rerun will not fix this",
                url, details[url]["category"], details[url]["upc"],
            )
    not_attempted = books["url"].nunique() - len(details) - len(download_failures)
    logger.info(
        "book pages: %d parsed, %d download failures (not saved, a rerun retries them), "
        "%d parse failures (saved, parser needs review), %d not attempted",
        len(details) - len(parse_failures), len(download_failures), len(parse_failures), not_attempted,
    )
    detail_frame = pd.DataFrame.from_dict(details, orient="index", columns=["category", "upc"]).astype("string")
    return books.join(detail_frame, on="url")


def check_books(books: pd.DataFrame, expected_rows: int) -> list[str]:
    """Every way the table falls short of expected_rows complete, distinct books (empty list if none)."""
    problems = []
    if len(books) != expected_rows:
        problems.append(f"expected {expected_rows} rows, got {len(books)}")
    if books["url"].nunique() != expected_rows:
        problems.append(f"expected {expected_rows} unique book urls, got {books['url'].nunique()}")
    for column in ("category", "upc"):
        blank = books[column].isna() | (books[column].str.strip() == "")
        if blank.any():
            problems.append(f"{int(blank.sum())} rows have a blank {column}: run is incomplete")
    duplicated_upc = books[books["upc"].notna() & books.duplicated(subset="upc", keep=False)]
    if not duplicated_upc.empty:
        listing = duplicated_upc.sort_values("upc")[["upc", "title", "url"]].to_string(index=False)
        problems.append(f"{len(duplicated_upc)} rows share a upc with another row, cause unknown, investigate:\n{listing}")
    return problems
