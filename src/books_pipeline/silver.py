"""Type the scraped strings, join the Open Library fields, and summarise the silver table."""
import logging

import pandas as pd

from books_pipeline.config import DataPaths

logger = logging.getLogger(__name__)

RATING = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def type_books(books: pd.DataFrame, scraped_at: pd.Timestamp) -> pd.DataFrame:
    """Add typed columns (price_gbp, rating_int, in_stock, scraped_at) and drop repeated title+url rows."""
    typed = books.copy()
    typed["price_gbp"] = typed["price"].str.replace("£", "").astype("float64")
    typed["rating_int"] = typed["rating"].map(RATING).astype("Int64")
    typed["in_stock"] = typed["availability"].str.contains("In stock")
    typed["scraped_at"] = scraped_at
    before = len(typed)
    typed = typed.drop_duplicates(subset=["title", "url"])
    if len(typed) < before:
        logger.warning("dropped %d rows repeating an earlier title+url", before - len(typed))
    logger.info("typed books shape: %s", typed.shape)
    return typed


def build_silver(typed_books: pd.DataFrame, enrichment: pd.DataFrame) -> pd.DataFrame:
    """Left-join the Open Library fields onto every book and add the publication decade."""
    silver = typed_books.merge(enrichment, on="title", how="left")
    if len(silver) != len(typed_books):
        logger.warning("join changed the row count from %d to %d (repeated titles)", len(typed_books), len(silver))
    silver["decade"] = (silver["first_publish_year"] // 10 * 10).astype("Int64")
    logger.info("silver shape: %s", silver.shape)
    return silver


def aggregate_by_rating(silver: pd.DataFrame) -> pd.DataFrame:
    """Number of books and average price per star rating."""
    return silver.groupby("rating_int").agg(n_books=("title", "count"), avg_price=("price_gbp", "mean")).round(2)


def aggregate_by_decade(silver: pd.DataFrame) -> pd.DataFrame:
    """Number of books and average price per first-publication decade (matched books only)."""
    return silver.groupby("decade").agg(n_books=("title", "count"), avg_price=("price_gbp", "mean")).round(2)


def write_silver(silver: pd.DataFrame, paths: DataPaths) -> None:
    """Save the silver table as Parquet and CSV."""
    paths.root.mkdir(parents=True, exist_ok=True)
    silver.to_parquet(paths.silver_parquet, index=False)
    silver.to_csv(paths.silver_csv, index=False)
    logger.info("wrote %s and %s", paths.silver_parquet, paths.silver_csv)
