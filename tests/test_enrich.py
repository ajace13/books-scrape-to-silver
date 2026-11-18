"""Tests for Open Library enrichment, run against saved JSON responses. No network."""
import json
import shutil
from pathlib import Path

from books_pipeline.enrich import enrich_titles, parse_search_result, safe_name


def load_payload(fixtures_dir: Path, name: str) -> dict:
    return json.loads((fixtures_dir / "api" / name).read_text(encoding="utf-8"))


def test_safe_name_matches_saved_file_names() -> None:
    assert safe_name("Sapiens: A Brief History of Humankind") == "sapiens-a-brief-history-of-humankind"


def test_correct_match_is_flattened(fixtures_dir: Path) -> None:
    row = parse_search_result("A Light in the Attic", load_payload(fixtures_dir, "a-light-in-the-attic.json"))
    assert row["author"] == "Shel Silverstein"
    assert row["first_publish_year"] == 1981
    assert row["n_subjects"] == 25


def test_title_only_match_can_return_a_different_book(fixtures_dir: Path) -> None:
    """Known data-quality issue: the top hit for Sapiens is a summary book, not Harari's."""
    payload = load_payload(fixtures_dir, "sapiens-a-brief-history-of-humankind.json")
    row = parse_search_result("Sapiens: A Brief History of Humankind", payload)
    assert row["author"] == "BookNation"
    assert row["ol_title"].startswith("Summary of Sapiens")


def test_no_match_gives_none_fields() -> None:
    row = parse_search_result("Not A Real Book", {"docs": []})
    assert row == {
        "title": "Not A Real Book", "ol_title": None, "author": None,
        "first_publish_year": None, "edition_count": None, "n_subjects": None,
    }


def test_failed_request_gives_none_fields() -> None:
    assert parse_search_result("Any Title", None)["ol_title"] is None


def test_enrich_titles_reads_from_cache(fixtures_dir: Path, tmp_path: Path) -> None:
    api_dir = tmp_path / "api"
    shutil.copytree(fixtures_dir / "api", api_dir)
    enrichment = enrich_titles(["A Light in the Attic", "Sapiens: A Brief History of Humankind"], api_dir)
    assert enrichment.shape == (2, 6)
    assert enrichment["ol_title"].notna().all()
