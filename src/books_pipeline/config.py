"""URLs, request settings and data paths shared by the pipeline."""
import os
from dataclasses import dataclass
from pathlib import Path

START_URL = "http://books.toscrape.com/catalogue/page-1.html"
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_FIELDS = "title,author_name,first_publish_year,isbn,subject,edition_count"

PAUSE_SECONDS = 1.0  # one request per second
REQUEST_TIMEOUT_SECONDS = 20
BOOKS_PER_PAGE = 20
SITE_PAGE_COUNT = 50
MAX_CONSECUTIVE_DOWNLOAD_FAILURES = 5
DEFAULT_CONTACT = "contact not set"


def user_agent() -> str:
    """User-Agent sent with every request, naming the project and the BOOKS_SCRAPER_CONTACT address."""
    contact = os.environ.get("BOOKS_SCRAPER_CONTACT", DEFAULT_CONTACT)
    return f"books-scrape-to-silver/0.1 ({contact})"


@dataclass(frozen=True)
class DataPaths:
    """Where each layer of the pipeline lives under one data folder."""

    root: Path

    @property
    def raw(self) -> Path:
        """Catalogue pages, saved exactly as served (bronze)."""
        return self.root / "raw"

    @property
    def books(self) -> Path:
        """Each book's own page, saved exactly as served (bronze)."""
        return self.raw / "books"

    @property
    def api(self) -> Path:
        """Open Library search responses, one JSON file per title (bronze)."""
        return self.root / "api"

    @property
    def silver_parquet(self) -> Path:
        return self.root / "books_silver.parquet"

    @property
    def silver_csv(self) -> Path:
        return self.root / "books_silver.csv"
