"""Look titles up in the Open Library Search API, caching every response as JSON."""
import logging
import re
from pathlib import Path

import pandas as pd

from books_pipeline.config import OPEN_LIBRARY_FIELDS, OPEN_LIBRARY_SEARCH_URL
from books_pipeline.fetch import load_json

logger = logging.getLogger(__name__)


def safe_name(title: str) -> str:
    """File-system-safe slug for a title, used to name its cached JSON response."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower())[:80]


def parse_search_result(title: str, payload: dict | None) -> dict:
    """Flatten the top Open Library match for title. Fields are None when there is no match or no response.

    The match is on title alone, so the top result can be a different book with the same title.
    """
    docs = (payload or {}).get("docs") or []
    top_doc = docs[0] if docs else {}
    return {
        "title": title,
        "ol_title": top_doc.get("title"),
        "author": (top_doc.get("author_name") or [None])[0],
        "first_publish_year": top_doc.get("first_publish_year"),
        "edition_count": top_doc.get("edition_count"),
        "n_subjects": len(top_doc.get("subject") or []) if docs else None,
    }


def lookup_title(title: str, api_dir: Path) -> dict:
    """Best Open Library match for one title, read from api_dir if saved, otherwise fetched and saved."""
    params = {"title": title, "limit": 1, "fields": OPEN_LIBRARY_FIELDS}
    payload = load_json(OPEN_LIBRARY_SEARCH_URL, params, api_dir / f"{safe_name(title)}.json")
    return parse_search_result(title, payload)


def enrich_titles(titles: list[str], api_dir: Path) -> pd.DataFrame:
    """One row per title with its Open Library fields; unmatched titles keep None."""
    api_dir.mkdir(parents=True, exist_ok=True)
    enrichment = pd.DataFrame([lookup_title(title, api_dir) for title in titles])
    logger.info("open library: %d of %d titles matched", enrichment["ol_title"].notna().sum(), len(enrichment))
    return enrichment
