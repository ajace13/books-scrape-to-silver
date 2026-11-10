"""Tests for the cached fetch layer and request settings. No network."""
import shutil
from pathlib import Path

import pytest
import requests

from books_pipeline import config, fetch


def test_load_html_reads_saved_page_without_a_request(fixtures_dir: Path, tmp_path: Path) -> None:
    saved = tmp_path / "page-1.html"
    shutil.copy(fixtures_dir / "page-1.html", saved)
    html = fetch.load_html("http://books.toscrape.com/catalogue/page-1.html", saved)
    assert "A Light in the Attic" in html


def test_load_json_reads_saved_response_without_a_request(fixtures_dir: Path) -> None:
    payload = fetch.load_json("https://openlibrary.org/search.json", {}, fixtures_dir / "api" / "a-light-in-the-attic.json")
    assert payload["docs"][0]["title"] == "A Light in the Attic"


def test_polite_get_returns_none_on_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_get(*args, **kwargs):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(requests, "get", failing_get)
    monkeypatch.setattr(fetch.time, "sleep", lambda seconds: None)
    assert fetch.polite_get("http://books.toscrape.com/catalogue/page-999.html") is None


def test_failed_download_saves_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fetch, "polite_get", lambda url, params=None: None)
    target = tmp_path / "page-2.html"
    assert fetch.load_html("http://books.toscrape.com/catalogue/page-2.html", target) is None
    assert not target.exists()


def test_user_agent_uses_contact_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKS_SCRAPER_CONTACT", "someone@example.com")
    assert "someone@example.com" in config.user_agent()


def test_user_agent_default_has_no_personal_contact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOOKS_SCRAPER_CONTACT", raising=False)
    assert config.user_agent() == f"books-scrape-to-silver/0.1 ({config.DEFAULT_CONTACT})"
