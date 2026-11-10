## Data Dictionary

There are two tables in this project. Only the first is saved to a file.

### 1. `books_silver.csv` and `books_silver.parquet`

Written by the notebook (Part 3). 100 rows, one per book on the first five catalogue pages, 16 columns. The Open Library columns are looked up for the first 20 titles only, so they are missing for the other 80 rows.

| column | type | meaning | source |
|---|---|---|---|
| title | string | book title as shown on the site | `h3 > a[title]` |
| price | string | price of book as shown on the site | `p.price_color` |
| rating | string | book rating out of 5 stars | `p.star-rating["class"][1]`|
| availability | string | string of whether the book is available or not| `p.instock.availability` |
| url | string | url of specific book| `h3 > a[href]` |
| page | int| page number the book is contained on | `n += 1` in `scrape()` function |
| price_gbp | float | price as a number, with the £ sign removed | `books["price"].str.replace("£", "").astype("float64")` |
| rating_int | Int64 (nullable integer) | rating column turned into an integer| `books["rating"].map(RATING).astype("Int64")` |
| in_stock | boolean | true or false for if the book is in stock | `books["availability"].str.contains("In stock")` |
| scraped_at | datetime64| UTC timestamp when the notebook's cleaning step (Part 3) runs; the same value for every row, not the time each page was downloaded | `pd.Timestamp.utcnow()` |
| ol_title | string | Open Library title of book | `d.get("title")` |
| author | string | author of the book| `(d.get("author_name") or [None])[0]` |
| first_publish_year | float | year the matched Open Library work was first published; missing when there is no match. The match is on title alone, so it can be a different book with the same title | `d.get("first_publish_year")` |
| edition_count | float | number of editions Open Library lists for the matched work; missing when there is no match | `d.get("edition_count")` |
| n_subjects | float | number of subject tags on the matched Open Library record; 0 when a looked-up title has no match or no subjects, missing for titles that were not looked up | `len(d.get("subject", []))` |
| decade | Int64 (nullable integer) | decade the book was published in | `(merged["first_publish_year"] // 10 * 10).astype("Int64")` |

### 2. The scraper DataFrame (`scrape.py`)

Built in memory by `python scrape.py`. 1,000 rows, one per book in the whole catalogue (50 pages), 8 columns. **It is not saved to a file: `category` and `upc` are not in `books_silver.csv` or `books_silver.parquet`.**

The first six columns (`title`, `price`, `rating`, `availability`, `url`, `page`) mean the same as in table 1. The two below come from each book's own page.

| column | type | meaning | source |
|---|---|---|---|
| category | string | category the site files the book under, exactly as shown. 50 distinct values, including the site's own `Default` and `Add a comment` | book page: `ul.breadcrumb li:nth-of-type(3) a` |
| upc | string | the site's product code for the book, e.g. `a897fe39b1053632`; different for every one of the 1,000 books. Kept as text, never converted to a number | book page: the `td` next to `<th>UPC</th>` in `table.table-striped` |
