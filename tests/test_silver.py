"""Tests for typing, joining and summarising the silver table. No network."""
import pandas as pd
import pytest

from books_pipeline.silver import aggregate_by_decade, aggregate_by_rating, build_silver, type_books

SCRAPED_AT = pd.Timestamp("2026-01-01", tz="UTC")


@pytest.fixture
def raw_books() -> pd.DataFrame:
    return pd.DataFrame({
        "title": ["A Light in the Attic", "Tipping the Velvet", "Soumission"],
        "price": ["£51.77", "£53.74", "£50.10"],
        "rating": ["Three", "One", "One"],
        "availability": ["In stock", "In stock", "Out of stock"],
        "url": ["u1", "u2", "u3"],
        "page": [1, 1, 1],
    })


@pytest.fixture
def enrichment() -> pd.DataFrame:
    return pd.DataFrame({
        "title": ["A Light in the Attic", "Tipping the Velvet"],
        "ol_title": ["A Light in the Attic", None],
        "author": ["Shel Silverstein", None],
        "first_publish_year": [1981, None],
        "edition_count": [27, None],
        "n_subjects": [25, 0],
    })


def test_type_books_dtypes(raw_books: pd.DataFrame) -> None:
    typed = type_books(raw_books, SCRAPED_AT)
    assert str(typed["price_gbp"].dtype) == "float64"
    assert str(typed["rating_int"].dtype) == "Int64"
    assert str(typed["in_stock"].dtype) == "bool"
    assert typed["price_gbp"].tolist() == [51.77, 53.74, 50.10]
    assert typed["in_stock"].tolist() == [True, True, False]


def test_type_books_drops_repeated_title_and_url(raw_books: pd.DataFrame) -> None:
    doubled = pd.concat([raw_books, raw_books.head(1)], ignore_index=True)
    assert len(type_books(doubled, SCRAPED_AT)) == 3


def test_left_join_keeps_every_book(raw_books: pd.DataFrame, enrichment: pd.DataFrame) -> None:
    silver = build_silver(type_books(raw_books, SCRAPED_AT), enrichment)
    assert len(silver) == 3
    assert silver["ol_title"].notna().sum() == 1


def test_decade_from_first_publish_year(raw_books: pd.DataFrame, enrichment: pd.DataFrame) -> None:
    silver = build_silver(type_books(raw_books, SCRAPED_AT), enrichment)
    assert silver.loc[0, "decade"] == 1980
    assert silver["decade"].isna().sum() == 2


def test_aggregates(raw_books: pd.DataFrame, enrichment: pd.DataFrame) -> None:
    silver = build_silver(type_books(raw_books, SCRAPED_AT), enrichment)
    by_rating = aggregate_by_rating(silver)
    assert by_rating.loc[1, "n_books"] == 2
    assert by_rating.loc[1, "avg_price"] == pytest.approx(51.92)
    by_decade = aggregate_by_decade(silver)
    assert by_decade.index.tolist() == [1980]
