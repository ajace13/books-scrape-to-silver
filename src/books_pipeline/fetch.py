"""Polite HTTP requests with an on-disk cache: a page or response already saved is never fetched again."""
import json
import logging
import time
from pathlib import Path

import requests

from books_pipeline.config import PAUSE_SECONDS, REQUEST_TIMEOUT_SECONDS, user_agent

logger = logging.getLogger(__name__)


def polite_get(url: str, params: dict | None = None) -> requests.Response | None:
    """One GET after a one-second pause. Returns None (and logs why) instead of raising on a failed request."""
    time.sleep(PAUSE_SECONDS)
    try:
        response = requests.get(url, params=params, headers={"User-Agent": user_agent()}, timeout=REQUEST_TIMEOUT_SECONDS)
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
    response = polite_get(url)
    if response is None:
        return None
    path.write_bytes(response.content)  # bronze: the bytes exactly as served
    logger.info("fetched %s and saved to %s", url, path.name)
    return response.content.decode("utf-8")  # the site sends no charset, so decode explicitly


def load_json(url: str, params: dict, path: Path) -> dict | None:
    """JSON response: read from path if saved, otherwise fetched and saved there. None if the request fails."""
    if path.exists():
        logger.debug("read %s from disk", path.name)
        return json.loads(path.read_text(encoding="utf-8"))
    response = polite_get(url, params=params)
    if response is None:
        return None
    payload = response.json()
    path.write_text(json.dumps(payload), encoding="utf-8")
    logger.info("fetched %s %s and saved to %s", url, params, path.name)
    return payload
