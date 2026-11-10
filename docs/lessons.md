# Data-quality lessons

## Matching on title alone is not enough

The Open Library Search API always returns *something* ranked first, and the pipeline takes that top hit. Of 20 titles looked up, 15 came back with a match. I hand-checked five of them against the saved responses:

| Book on the site | Top Open Library hit | Verdict |
|---|---|---|
| A Light in the Attic | Shel Silverstein, 1981 | right book |
| Sharp Objects | Gillian Flynn | right book |
| Sapiens: A Brief History of Humankind | "Summary of Sapiens" by BookNation, 2020 | **wrong book**: a summary, not Yuval Noah Harari's book |
| Shakespeare's Sonnets | a 1999 book credited to James Schiffer | **wrong book**: a book about the sonnets |
| Set Me Free | Denise Robins, one of 120 results | can't confirm: the shop page gives no author to compare against |

So 2 of 5 checks were wrong, and one couldn't be decided. A wrong match carries a wrong `author`, `first_publish_year`, `edition_count` and `decade`, and those flow straight into the per-decade averages as if they were correct. Study guides, books about the book, and unrelated books sharing a title all count as matches.

What would fix it: match on title **and** author (the shop pages don't list authors, so that needs another source), or on ISBN, or reject a match when the returned title differs from the scraped one by more than a set threshold. The Sapiens mismatch is pinned in `tests/test_enrich.py` so it stays visible.

## Other things the data taught me

- **Encoding.** The site sends no charset, so `requests` guesses ISO-8859-1 and `£` turns into `Â£`. The first version of the price test failed for exactly that reason. The fix was to decode the saved bytes as UTF-8 and repair the saved pages, not to loosen the test.
- **Odd categories are real.** Two category names, `Default` and `Add a comment`, look like scraping bugs but are what the site shows. They are kept as scraped.
- **Product codes are text.** `upc` values like `a897fe39b1053632` must stay strings; read the CSV back with `dtype={"upc": "string"}`.
- **Download failures and parse failures need different responses.** A failed download isn't saved, so a rerun retries it. A page that downloads but doesn't parse is saved, so rerunning won't help: the parser needs a look. The crawler reports the two counts separately.
- **Cache everything.** Every page and API response is saved before parsing, so re-parsing after a fix makes no requests. A full run from an empty cache is about 1,050 requests (roughly 20 minutes at one per second); a cached run takes about 25 seconds.

## Where Claude was wrong or needed me

I built the first version of this project with Claude as a coding assistant. In my own words, from my write-up at the time:

> Claude wrote a lot of the extended scraper, but I still had to review its explanations and the assumptions it was making. Its first suggestion for the book-page selectors came from memory, so I asked it to check an actual page before using them. It also claimed that running the encoding repair again would fail safely, which turned out to be wrong. The repair we ended up with used backups and validation before replacing any files. I asked for download and parsing failures to be reported separately, and for a guard in case the catalogue came back empty. While reviewing the documentation, I also had to make sure the 1,000-row table in memory wasn’t confused with the 100-row silver files. I also had to stop the prompt log from getting overwritten. This made me realize that reviewing generated code is about more than whether the program finishes. It also means checking the data, how the code behaves when something fails, and the documentation.
