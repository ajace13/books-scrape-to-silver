"""Scrape books.toscrape.com, enrich titles from Open Library, and write the silver table."""
import argparse
import logging
from pathlib import Path

import pandas as pd

from books_pipeline.config import BOOKS_PER_PAGE, SITE_PAGE_COUNT, DataPaths
from books_pipeline.crawl import add_book_details, check_books, walk_catalogue
from books_pipeline.enrich import enrich_titles
from books_pipeline.silver import aggregate_by_decade, aggregate_by_rating, build_silver, type_books, write_silver

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command-line options."""
    parser = argparse.ArgumentParser(prog="python -m books_pipeline", description=__doc__)
    parser.add_argument("--pages", type=int, default=SITE_PAGE_COUNT, help="catalogue pages to walk (the site has 50)")
    parser.add_argument("--enrich-limit", type=int, default=20, help="how many titles to look up in Open Library")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="folder for raw pages, API responses and silver files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run scrape, book details, checks, enrichment and silver. Returns 0 on success, 1 if incomplete."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    args = parse_args(argv)
    paths = DataPaths(args.data_dir)

    books = walk_catalogue(paths, max_pages=args.pages)
    logger.info("books shape after catalogue walk: %s", books.shape)
    if books.empty or "url" not in books.columns:
        logger.error("run INCOMPLETE: the catalogue walk gave no book urls")
        return 1
    books = add_book_details(books, paths)
    logger.info("books shape after book details: %s", books.shape)

    expected_rows = BOOKS_PER_PAGE * min(args.pages, SITE_PAGE_COUNT)
    problems = check_books(books, expected_rows)
    for problem in problems:
        logger.error(problem)
    if problems:
        logger.error("run INCOMPLETE: %d checks failed; saved pages are kept, rerun to retry failed downloads", len(problems))
        return 1

    enrichment = enrich_titles(books["title"].head(args.enrich_limit).tolist(), paths.api)
    silver = build_silver(type_books(books, scraped_at=pd.Timestamp.now(tz="UTC")), enrichment)
    write_silver(silver, paths)
    logger.info("by rating:\n%s", aggregate_by_rating(silver))
    logger.info("by decade:\n%s", aggregate_by_decade(silver))
    logger.info("run complete: all checks passed")
    return 0
