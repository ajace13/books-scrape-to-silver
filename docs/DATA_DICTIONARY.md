# Data dictionary

## `data/books_silver.parquet` and `data/books_silver.csv`

Written by `python -m books_pipeline`. With `--pages 50` (the default): 1,000 rows, one per book in the catalogue, 18 columns. Open Library fields are looked up for the first `--enrich-limit` titles only (default 20), so they are missing for the other rows.

`data/sample/books_silver_sample.csv` is the first 25 rows of the notebook's version of this table. The notebook walks only five pages and doesn't visit book pages, so the sample has 16 columns: no `category` or `upc`.

| column | type | meaning | source |
|---|---|---|---|
| title | string | book title as shown on the site | catalogue page: `h3 > a[title]` |
| price | string | price as shown on the site, e.g. `£51.77` | catalogue page: `p.price_color` |
| rating | string | star rating as a word, `One` to `Five` | catalogue page: `p.star-rating["class"][1]` |
| availability | string | stock text as shown on the site | catalogue page: `p.instock.availability` |
| url | string | absolute URL of the book's own page | catalogue page: `h3 > a[href]` joined to the page URL |
| page | int64 | catalogue page the book was listed on | counter in `crawl.walk_catalogue()` |
| category | string | category the site files the book under, exactly as shown. 50 distinct values, including the site's own `Default` and `Add a comment` | book page: `ul.breadcrumb li:nth-of-type(3) a` |
| upc | string | the site's product code, e.g. `a897fe39b1053632`; different for every book. Kept as text, never converted to a number | book page: the `td` next to `<th>UPC</th>` |
| price_gbp | float64 | price as a number, with the £ sign removed | `price` in `silver.type_books()` |
| rating_int | Int64 (nullable integer) | star rating as 1 to 5 | `rating` mapped through `silver.RATING` |
| in_stock | bool | whether the availability text contains "In stock" | `availability` in `silver.type_books()` |
| scraped_at | datetime64[us, UTC] | when the silver step ran; the same value for every row, not when each page was downloaded | `pd.Timestamp.now(tz="UTC")` in `cli.main()` |
| ol_title | string | title of the top Open Library match; missing when there is no match | API: `docs[0].title` |
| author | string | first author of the top match; missing when there is no match | API: `docs[0].author_name[0]` |
| first_publish_year | float64 | year the matched work was first published; missing when there is no match. The match is on title alone, so it can be a different book with the same title (see `lessons.md`) | API: `docs[0].first_publish_year` |
| edition_count | float64 | number of editions Open Library lists for the matched work; missing when there is no match | API: `docs[0].edition_count` |
| n_subjects | float64 | number of subject tags on the matched record. 0 when the match has no subjects; missing when there is no match or the title was not looked up | API: `len(docs[0].subject)` |
| decade | Int64 (nullable integer) | decade of `first_publish_year`, e.g. 1980; missing when there is no match | `first_publish_year // 10 * 10` in `silver.build_silver()` |

## Bronze files (not committed)

| path | contents |
|---|---|
| `data/raw/page-N.html` | each catalogue page, the bytes exactly as served |
| `data/raw/books/<slug>.html` | each book's own page, named after its URL folder |
| `data/api/<title-slug>.json` | each Open Library search response, as returned |
