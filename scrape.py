"""Scrape every books.toscrape.com catalogue page into data/raw and return the books as a DataFrame."""
import logging
import os
import sys
import time
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
BOOKS_DIR = RAW_DIR / "books"

START_URL = "http://books.toscrape.com/catalogue/page-1.html"
CONTACT = os.environ.get("BOOKS_SCRAPER_CONTACT", "contact not set")
HEADERS = {"User-Agent": f"books-scrape-to-silver/0.1 ({CONTACT})"}
PAUSE = 1.0  # one request per second
MAX_PAGES = 50
EXPECTED_BOOKS = 1000
MAX_CONSECUTIVE_DOWNLOAD_FAILURES = 5

logger = logging.getLogger(__name__)


def get(url: str) -> requests.Response | None:
    """One polite GET. Returns None (and logs why) instead of crashing on a bad page."""
    time.sleep(PAUSE)
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response
    except requests.RequestException as error:
        logger.warning("skipped %s: %s", url, error)
        return None


def load_html(url: str, path: Path) -> str | None:
    """HTML of one page: read from path if saved, otherwise fetched and saved there. None if the download fails."""
    if path.exists():
        logger.debug("read %s from disk", path.name)
        return path.read_bytes().decode("utf-8")
    response = get(url)
    if response is None:
        return None
    path.write_bytes(response.content)  # Bronze: the bytes exactly as served
    logger.info("fetched %s and saved to %s", url, path.name)
    return response.content.decode("utf-8")


def book_path(book_url: str) -> Path:
    """Where one book's own page is saved, named after its URL folder (e.g. a-light-in-the-attic_1000)."""
    slug = PurePosixPath(urlparse(book_url).path).parent.name
    return BOOKS_DIR / f"{slug}.html"


def parse_page(html: str) -> list[dict]:
    """All books on one catalogue page: title, price, rating, availability, url (strings)."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for pod in soup.select("article.product_pod"):
        rows.append({
            "title": pod.h3.a["title"],
            "price": pod.select_one("p.price_color").get_text(strip=True),
            "rating": pod.select_one("p.star-rating")["class"][1],
            "availability": pod.select_one("p.instock.availability").get_text(strip=True),
            "url": urljoin(START_URL, pod.h3.a["href"]),
        })
    return rows


def next_url(html: str, page_url: str) -> str | None:
    """Absolute URL of the next catalogue page, or None when there isn't one."""
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    return urljoin(page_url, next_link["href"]) if next_link else None


def scrape(start_url: str = START_URL, max_pages: int = MAX_PAGES) -> pd.DataFrame:
    """Follow 'next' from start_url until there is no next link, one row per book."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    url = start_url
    page_number = 0
    while url and page_number < max_pages:
        page_number += 1
        html = load_html(url, RAW_DIR / f"page-{page_number}.html")
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


def parse_book(html: str) -> dict:
    """category and upc from one book's own page, as strings exactly as shown (None if the element is missing)."""
    soup = BeautifulSoup(html, "html.parser")
    category_link = soup.select_one("ul.breadcrumb li:nth-of-type(3) a")  # Home > Books > category > title
    upc_header = soup.find("th", string="UPC")
    upc_cell = upc_header.find_next_sibling("td") if upc_header else None
    return {
        "category": category_link.get_text(strip=True) if category_link else None,
        "upc": upc_cell.get_text(strip=True) if upc_cell else None,
    }


def add_book_details(books: pd.DataFrame) -> pd.DataFrame:
    """Add category and upc from each book's own page. Both stay missing for a book whose page fails."""
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    details = {}
    download_failures = []
    parse_failures = []
    consecutive_download_failures = 0
    for url in books["url"].unique():
        html = load_html(url, book_path(url))
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
                "parse failure: %s is saved as %s but gave category=%r upc=%r; review the parser, a rerun will not fix this",
                url, book_path(url).name, details[url]["category"], details[url]["upc"],
            )
    not_attempted = books["url"].nunique() - len(details) - len(download_failures)
    logger.info(
        "book pages: %d parsed, %d download failures (not saved, a rerun retries them), "
        "%d parse failures (saved, parser needs review), %d not attempted",
        len(details) - len(parse_failures), len(download_failures), len(parse_failures), not_attempted,
    )
    detail_frame = pd.DataFrame.from_dict(details, orient="index", columns=["category", "upc"]).astype("string")
    return books.join(detail_frame, on="url")


def check_books(books: pd.DataFrame) -> list[str]:
    """Every way the finished table falls short of 1000 complete, distinct books (empty list if none)."""
    problems = []
    if len(books) != EXPECTED_BOOKS:
        problems.append(f"expected {EXPECTED_BOOKS} rows, got {len(books)}")
    if books["url"].nunique() != EXPECTED_BOOKS:
        problems.append(f"expected {EXPECTED_BOOKS} unique book urls, got {books['url'].nunique()}")
    for column in ("category", "upc"):
        blank = books[column].isna() | (books[column].str.strip() == "")
        if blank.any():
            problems.append(f"{int(blank.sum())} rows have a blank {column}: run is incomplete")
    duplicated_upc = books[books["upc"].notna() & books.duplicated(subset="upc", keep=False)]
    if not duplicated_upc.empty:
        listing = duplicated_upc.sort_values("upc")[["upc", "title", "url"]].to_string(index=False)
        problems.append(f"{len(duplicated_upc)} rows share a upc with another row, cause unknown, investigate:\n{listing}")
    return problems


def main() -> int:
    """Run the full scrape and fail loudly if the result is incomplete."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    books_raw = scrape()
    logger.info("books_raw shape after catalogue walk: %s", books_raw.shape)
    if books_raw.empty or "url" not in books_raw.columns:
        logger.error("run INCOMPLETE: the catalogue walk gave no book urls, so there are no book pages to visit")
        return 1
    books_raw = add_book_details(books_raw)
    logger.info("books_raw shape after book details: %s", books_raw.shape)
    problems = check_books(books_raw)
    for problem in problems:
        logger.error(problem)
    if problems:
        logger.error("run INCOMPLETE: %d checks failed; saved pages are kept, rerun to retry failed downloads", len(problems))
        return 1
    logger.info("run complete: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
