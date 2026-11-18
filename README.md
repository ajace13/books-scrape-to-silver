# books-scrape-to-silver

A small, polite web-scraping pipeline that turns the practice bookshop [books.toscrape.com](http://books.toscrape.com) into a typed, analysis-ready table. It walks all 50 catalogue pages and visits all 1,000 book pages, enriches titles from the Open Library Search API, and writes a silver Parquet file. Every page and API response is cached on disk first, so reruns make no requests and the tests run fully offline.

```mermaid
flowchart LR
    A[Scrape<br/>books.toscrape.com<br/>+ Open Library API] -->|one request per second| B[Bronze<br/>raw HTML in data/raw<br/>raw JSON in data/api]
    B -->|BeautifulSoup parse<br/>pandas typing + left join| C[Silver<br/>typed table]
    C --> D[books_silver.parquet<br/>books_silver.csv]
```

## Run it in three commands

```bash
python -m pip install -r requirements.txt -e .
python -m books_pipeline --pages 50
python -m pytest -q
```

1. **Install** the dependencies and the `books_pipeline` package.
2. **Run the pipeline.** It walks the catalogue, visits each book page for `category` and `upc`, checks the result (expected row count, unique URLs, no blank `category` or `upc`, no repeated `upc`), looks up the first 20 titles in Open Library, and writes `data/books_silver.parquet` and `.csv`. It ends with `run complete` (exit 0) or `run INCOMPLETE` (exit 1). From an empty cache that is about 1,050 requests at one per second, roughly 20 minutes; a cached rerun takes about 25 seconds.
3. **Test.** 31 tests against saved HTML pages and JSON responses in `tests/fixtures/`. `requests.get` is patched to raise, so no test can touch the network.

Set `BOOKS_SCRAPER_CONTACT` to your email before scraping so the sites can reach you; it goes in the User-Agent. Options: `--enrich-limit N` (titles to look up, default 20) and `--data-dir PATH` (default `data`).

## Layout

```
src/books_pipeline/
├── config.py     URLs, request settings, data paths, User-Agent
├── fetch.py      one polite GET; load HTML/JSON from cache or fetch and save
├── parse.py      catalogue page, next link, book page (pure functions)
├── crawl.py      catalogue walk, book details, completeness checks
├── enrich.py     Open Library lookup and flattening
├── silver.py     typing, left join, decade, aggregates, write
└── cli.py        python -m books_pipeline
tests/            31 offline tests + fixtures (3 HTML pages, 2 JSON responses)
notebooks/        analysis.ipynb, the original exploratory notebook with outputs
docs/             DATA_DICTIONARY.md, lessons.md
data/sample/      first 25 rows of the silver table
```

## Results

The full run collects **1,000 books** across 50 categories, every one with a unique `upc`, and the first 20 titles looked up in Open Library (15 matched).

**Books and average price by star rating, full catalogue (1,000 books)**

| rating | books | average price (GBP) |
|---|---|---|
| 1 | 226 | 34.56 |
| 2 | 196 | 34.81 |
| 3 | 203 | 34.69 |
| 4 | 179 | 36.09 |
| 5 | 196 | 35.37 |

**Books and average price by star rating, notebook sample (first five pages, 100 books)**

| rating | books | average price (GBP) |
|---|---|---|
| 1 | 22 | 35.52 |
| 2 | 19 | 35.91 |
| 3 | 22 | 36.84 |
| 4 | 18 | 33.98 |
| 5 | 19 | 30.01 |

**Average price by first-publication decade** (the 15 matched books only; identical in the notebook and the full run)

| decade | books | average price (GBP) |
|---|---|---|
| 1980 | 1 | 51.77 |
| 1990 | 3 | 30.62 |
| 2000 | 2 | 41.42 |
| 2010 | 7 | 39.80 |
| 2020 | 2 | 38.42 |

In the first 100 books five-star titles looked cheapest (£30.01), but over the full catalogue every star rating averages between £34.56 and £36.09, so that was a small-sample effect. The decade table rests on 15 title-only matches, some of them wrong (next section), so read it as a demonstration of the join, not a finding.

## Data-quality lessons

- **Title-only matching is unreliable.** In a hand check of five Open Library matches, 2 were the wrong book: *Sapiens* matched a 2020 summary book, and *Shakespeare's Sonnets* matched a book about the sonnets. Wrong matches feed wrong years into the decade averages. The fix: match on title plus author or ISBN (the shop pages list neither, so that needs another source), or reject a hit whose returned title differs too much from the scraped one. Until then the decade table is labelled as unreliable and the Sapiens mismatch is pinned in a test.
- **Encoding.** The site sends no charset, so `£` decoded as `Â£` until the bytes were decoded explicitly as UTF-8. A test on the price sign caught it.
- **Odd values can be real.** The categories `Default` and `Add a comment` are what the site shows, not scraping bugs.
- **Product codes stay text.** `upc` is never converted to a number.

More in [docs/lessons.md](docs/lessons.md); column definitions in [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

## How I used Claude and where it was wrong

I used Claude as a coding assistant to extend the scraper to all 50 pages, add the book-page details, write the tests and draft the docs. I reviewed each change before running it. From my write-up:

- Its first book-page selectors came from memory, so I had it check a real saved page before using them.
- It claimed rerunning its encoding repair would fail safely; it wouldn't. The repair we kept backs up and validates files before replacing them.
- I asked for download failures and parse failures to be reported separately, and for a guard against an empty catalogue.
- In the docs I had to keep the 1,000-row scraper table separate from the 100-row silver files, and stop the prompt log from being overwritten.

Reviewing generated code is about more than whether it finishes: it means checking the data, the failure behaviour and the documentation. The full paragraph is in [docs/lessons.md](docs/lessons.md).

## Scraping rules the code follows

- One request per second; the pause sits inside `fetch.polite_get()`, the only function that makes a request.
- Every request carries a User-Agent naming the project and a contact address.
- A page or response already saved is read from disk, never fetched again, and pages are saved as the exact bytes served.
- No API keys, passwords or tokens are needed.

---

Built for ADSP 31011 Cloud-Native Data Engineering, University of Chicago, Autumn 2026.
