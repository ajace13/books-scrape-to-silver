"""Pure HTML parsers for books.toscrape.com catalogue and book pages."""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from books_pipeline.config import START_URL


def parse_page(html: str) -> list[dict]:
    """All books on one catalogue page: title, price, rating, availability, url (strings)."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for pod in soup.select("article.product_pod"):
        rows.append({
            "title": pod.h3.a["title"],
            "price": pod.select_one("p.price_color").get_text(strip=True),
            "rating": pod.select_one("p.star-rating")["class"][1],
            "availability": pod.select_one("p.instock.availability").get_text(strip=True),
            "url": urljoin(START_URL, pod.h3.a["href"]),
        })
    return rows


def next_url(html: str, page_url: str) -> str | None:
    """Absolute URL of the next catalogue page, or None when there isn't one."""
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    return urljoin(page_url, next_link["href"]) if next_link else None


def parse_book(html: str) -> dict:
    """category and upc from one book's own page, as strings exactly as shown (None if the element is missing)."""
    soup = BeautifulSoup(html, "html.parser")
    category_link = soup.select_one("ul.breadcrumb li:nth-of-type(3) a")  # Home > Books > category > title
    upc_header = soup.find("th", string="UPC")
    upc_cell = upc_header.find_next_sibling("td") if upc_header else None
    return {
        "category": category_link.get_text(strip=True) if category_link else None,
        "upc": upc_cell.get_text(strip=True) if upc_cell else None,
    }
