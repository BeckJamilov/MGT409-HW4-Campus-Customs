"""Agent dependencies and tools.

- Problem 5: the dependency object the agent needs at run time.
- Problem 6: read-only database tools for product info, price, and stock.
- Problem 7: remember which products the tools returned and build page cards from them.
- Problem 8: customer and current-page context in ShopDeps.
- Problem 9: product categories and the filter_products tool (price / size / sort).
- Problem 12: every tool call is written to the audit trail (audit.py).

All tools are read-only: they open the database with mode=ro and run SELECT queries only.
"""

import json
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic_ai import ModelRetry, RunContext

from audit import audited_tool
from models import (
    FilteredProduct,
    FilteredProductsResult,
    ProductCard,
    ProductDetails,
    ProductMatch,
    ProductSearchResult,
    SizeStock,
    StockCheckResult,
)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
SIZE_ALIASES = {
    "xs": "XS", "extra small": "XS", "x-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "double xl": "XXL",
}
# Three catalogue rows hold an auto-generated stub instead of a real description.
STUB_DESCRIPTION_PREFIX = "Campus Customs product photo"
STOP_WORDS = {
    "a", "an", "the", "do", "you", "have", "any", "with", "on", "in", "of", "for", "and", "or",
    "is", "it", "me", "i", "show", "some", "what", "your", "yale", "items", "item", "something",
}
# Garment words that must not be stemmed ("shorts" -> "short" would match "short-sleeve").
NO_STEM = {"shorts", "pants", "sweatpants", "joggers", "leggings", "socks"}
DEFAULT_SEARCH_RESULTS = 8
MAX_SEARCH_RESULTS = 30
MAX_PAGE_PRODUCTS = 30
SHORT_DESCRIPTION_LENGTH = 110


@dataclass
class Customer:
    """The logged-in customer, loaded from the users table (Problem 8)."""

    user_id: int
    first_name: str | None
    last_name: str | None
    name: str
    email: str


@dataclass
class CurrentPage:
    """What the customer is looking at, verified against the database (Problem 8)."""

    path: str
    product_id: str | None = None
    product_name: str | None = None


@dataclass
class ShopDeps:
    """Per-request context passed to the agent and its tools."""

    db_path: Path = DEFAULT_DB_PATH
    # product_ids returned by tools during this request; only these may become page cards.
    seen_product_ids: set[str] = field(default_factory=set)
    customer: Customer | None = None  # None for guests
    page: CurrentPage | None = None
    run_id: str | None = None  # links audit_trail.json entries of one agent run (Problem 12)


def _connect(deps: ShopDeps) -> sqlite3.Connection:
    """Read-only connection: the tools can never change the database."""
    conn = sqlite3.connect(f"file:{deps.db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_size(size: str) -> str | None:
    return SIZE_ALIASES.get(size.strip().lower().replace("size", "").strip())


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    # Very light stemming so "hoodies" matches "hoodie" and "jackets" matches "jacket".
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") and w not in NO_STEM else w
            for w in words if w not in STOP_WORDS]


def _row_tokens(row: sqlite3.Row) -> tuple[set[str], set[str]]:
    """Searchable words of a catalogue row: (name words, all other words)."""
    name_tokens = set(_tokens(row["name"]))
    other_tokens = set(_tokens(" ".join([
        row["garment_type"], row["description"],
        *json.loads(row["colors"]), *json.loads(row["search_tags"]),
    ])))
    return name_tokens, other_tokens


def category_for(garment_type: str) -> str:
    """Group the 22 free-text garment_type spellings into a few shopper-friendly categories."""
    g = garment_type.lower()
    if "t-shirt" in g or "t shirt" in g:
        return "T-Shirts"
    if "quarter-zip" in g:
        return "Quarter-Zips"
    if "hood" in g:
        return "Hoodies"
    if "jacket" in g or "fleece" in g:
        return "Jackets & Fleece"
    if "long-sleeve" in g or "performance" in g:
        return "Long Sleeve & Performance"
    if "crewneck" in g or "mockneck" in g or "sweatshirt" in g:
        return "Crewnecks & Sweatshirts"
    return "Other"


def _load_sizes(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    sizes = [SizeStock(size=r["size"], quantity=r["quantity"], in_stock=r["quantity"] > 0) for r in rows]
    return sorted(sizes, key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99)


def _clean_description(description: str) -> str | None:
    return None if description.startswith(STUB_DESCRIPTION_PREFIX) else description


def _load_product(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    if row is None:
        # Tells the model to fix its call instead of inventing an answer.
        raise ModelRetry(
            f"No product with product_id '{product_id}'. Use find_products to get a valid product_id."
        )
    return row


def find_products(
    ctx: RunContext[ShopDeps], query: str, limit: int = DEFAULT_SEARCH_RESULTS
) -> ProductSearchResult:
    """Search the Campus Customs catalogue by keywords (product name, garment type, color, team,
    residential college, design). Use this first to turn what the customer says into real
    product_ids. Returns the best matches with name, garment type, and price.

    Args:
        query: Keywords from the customer, e.g. "bulldog hoodie", "hockey", "navy crewneck".
        limit: Max results (default 8, up to 30). Use a higher limit when the customer wants
            to browse a whole category, e.g. "what hoodies do you have?".
    """
    limit = max(1, min(limit, MAX_SEARCH_RESULTS))
    query_tokens = _tokens(query)
    if not query_tokens:
        raise ModelRetry("The query has no useful keywords. Try words like 'hoodie' or 'hockey'.")

    with closing(_connect(ctx.deps)) as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()

    scored = []
    for row in rows:
        name_tokens, other_tokens = _row_tokens(row)
        matched = [t for t in query_tokens if t in name_tokens or t in other_tokens]
        if not matched:
            continue
        # Rank by how many keywords matched; keywords in the product name count extra.
        score = len(set(matched)) * 2 + sum(t in name_tokens for t in set(matched))
        scored.append((score, row["name"], row))

    scored.sort(key=lambda item: (-item[0], item[1]))
    best = scored[0][0] if scored else 0
    # Keep only results as good as the top-scoring tier's keyword coverage.
    top = [row for score, _, row in scored if score >= best - 1]
    matches = [
        ProductMatch(product_id=r["product_id"], name=r["name"],
                     garment_type=r["garment_type"], price=r["price"])
        for r in top[:limit]
    ]
    ctx.deps.seen_product_ids.update(m.product_id for m in matches)
    return ProductSearchResult(query=query, matches=matches, total_matches=len(top))


def get_product_details(ctx: RunContext[ShopDeps], product_id: str) -> ProductDetails:
    """Get the full catalogue record for one product: description, colors, price, and the
    stock quantity for every size. Use this for any question about a product's description,
    price, or availability.

    Args:
        product_id: Exact product_id from find_products, e.g. "basic-hoodie-big-yale".
    """
    with closing(_connect(ctx.deps)) as conn:
        row = _load_product(conn, product_id)
        sizes = _load_sizes(conn, product_id)

    ctx.deps.seen_product_ids.add(product_id)
    description = _clean_description(row["description"])
    return ProductDetails(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=description,
        colors=json.loads(row["colors"]),
        price=row["price"],
        sizes=sizes,
        total_stock=sum(s.quantity for s in sizes),
        sizes_in_stock=[s.size for s in sizes if s.in_stock],
        sizes_out_of_stock=[s.size for s in sizes if not s.in_stock],
    )


def check_stock(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None) -> StockCheckResult:
    """Check how many units of a product are in stock, for one size or for all sizes.
    Sizes are XS, S, M, L, XL, XXL (words like "medium" or "extra large" also work).

    Args:
        product_id: Exact product_id from find_products.
        size: Size the customer asked about, or omit to get stock for every size.
    """
    with closing(_connect(ctx.deps)) as conn:
        row = _load_product(conn, product_id)
        sizes = _load_sizes(conn, product_id)
    ctx.deps.seen_product_ids.add(product_id)
    total = sum(s.quantity for s in sizes)
    base = dict(product_id=row["product_id"], name=row["name"], price=row["price"],
                sizes=sizes, total_stock=total)

    if size is None:
        in_stock = [s.size for s in sizes if s.in_stock]
        status = (f"{total} units in stock. Available sizes: {', '.join(in_stock)}."
                  if in_stock else "Sold out in every size.")
        return StockCheckResult(**base, requested_size=None, quantity=None, in_stock=None, status=status)

    normalized = normalize_size(size)
    if normalized is None:
        raise ModelRetry(f"'{size}' is not a valid size. Use one of: {', '.join(SIZE_ORDER)}.")
    match = next((s for s in sizes if s.size == normalized), None)
    quantity = match.quantity if match else 0
    status = f"{normalized} is out of stock." if quantity == 0 else f"{quantity} in stock in size {normalized}."
    return StockCheckResult(**base, requested_size=normalized, quantity=quantity,
                            in_stock=quantity > 0, status=status)


CategoryName = Literal[
    "T-Shirts", "Hoodies", "Crewnecks & Sweatshirts", "Quarter-Zips",
    "Jackets & Fleece", "Long Sleeve & Performance",
]


def filter_products(
    ctx: RunContext[ShopDeps],
    category: CategoryName | None = None,
    keywords: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    size_in_stock: str | None = None,
    sort: Literal["price_low_to_high", "price_high_to_low", "name"] = "price_low_to_high",
    limit: int = 10,
) -> FilteredProductsResult:
    """Find products that meet exact conditions, using the database: category, keywords,
    price range, and a size that must be in stock, sorted by price or name. Use this for
    questions like "hoodies under $70", "cheapest fleece", "most expensive jacket",
    "t-shirts in XL", or "anything under $40 in size S".

    Args:
        category: Product category to include (optional).
        keywords: Words that must all match the product (name, type, colors, tags,
            description), e.g. "fleece", "bulldog", "navy" (optional).
        min_price: Lowest price in USD, inclusive (optional).
        max_price: Highest price in USD, inclusive (optional). "Under $70" means max_price=70.
        size_in_stock: Only products with this size in stock, e.g. "M" or "large" (optional).
        sort: "price_low_to_high" (for "cheapest"), "price_high_to_low", or "name".
        limit: Max products to return (default 10, up to 30). Use 1–3 for "the cheapest".
    """
    limit = max(1, min(limit, MAX_SEARCH_RESULTS))
    size = None
    if size_in_stock:
        size = normalize_size(size_in_stock)
        if size is None:
            raise ModelRetry(f"'{size_in_stock}' is not a valid size. Use one of: {', '.join(SIZE_ORDER)}.")
    keyword_tokens = _tokens(keywords) if keywords else []

    # Price and size filters run in SQL; category/keyword matching runs in Python below.
    sql = """
        SELECT c.*,
               (SELECT group_concat(size) FROM inventory i
                WHERE i.product_id = c.product_id AND i.quantity > 0) AS sizes_in_stock,
               (SELECT quantity FROM inventory i
                WHERE i.product_id = c.product_id AND i.size = ?) AS size_quantity
        FROM catalogue c WHERE 1 = 1
    """
    params: list = [size]
    if min_price is not None:
        sql += " AND c.price >= ?"
        params.append(min_price)
    if max_price is not None:
        sql += " AND c.price <= ?"
        params.append(max_price)
    if size:
        sql += " AND EXISTS (SELECT 1 FROM inventory i WHERE i.product_id = c.product_id AND i.size = ? AND i.quantity > 0)"
        params.append(size)
    with closing(_connect(ctx.deps)) as conn:
        rows = conn.execute(sql, params).fetchall()

    matches = []
    for row in rows:
        if category and category_for(row["garment_type"]) != category:
            continue
        if keyword_tokens:
            name_tokens, other_tokens = _row_tokens(row)
            if not all(t in name_tokens or t in other_tokens for t in keyword_tokens):
                continue
        in_stock = (row["sizes_in_stock"] or "").split(",") if row["sizes_in_stock"] else []
        matches.append(FilteredProduct(
            product_id=row["product_id"],
            name=row["name"],
            category=category_for(row["garment_type"]),
            garment_type=row["garment_type"],
            price=row["price"],
            sizes_in_stock=sorted(in_stock, key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else 99),
            quantity_in_requested_size=row["size_quantity"] if size else None,
        ))

    sort_keys = {
        "name": lambda m: m.name,
        "price_low_to_high": lambda m: (m.price, m.name),
        "price_high_to_low": lambda m: (-m.price, m.name),
    }
    matches.sort(key=sort_keys[sort])

    shown = matches[:limit]
    ctx.deps.seen_product_ids.update(m.product_id for m in shown)
    return FilteredProductsResult(
        filters={k: v for k, v in {
            "category": category, "keywords": keywords, "min_price": min_price,
            "max_price": max_price, "size_in_stock": size, "sort": sort,
        }.items() if v is not None},
        products=shown,
        total_matches=len(matches),
    )


# Every tool call is recorded in output/audit_trail.json (Problem 12).
SHOP_TOOLS = [audited_tool(t) for t in (find_products, filter_products, get_product_details, check_stock)]


def build_product_cards(deps: ShopDeps, product_ids: list[str]) -> list[ProductCard]:
    """Turn the agent's chosen product_ids into page cards using database values only.

    Keeps the agent's order, drops duplicates and unknown ids, and caps the count.
    """
    unique_ids = list(dict.fromkeys(product_ids))[:MAX_PAGE_PRODUCTS]
    if not unique_ids:
        return []
    placeholders = ",".join("?" * len(unique_ids))
    with closing(_connect(deps)) as conn:
        rows = conn.execute(
            f"SELECT * FROM catalogue WHERE product_id IN ({placeholders})", unique_ids
        ).fetchall()
    by_id = {r["product_id"]: r for r in rows}

    cards = []
    for pid in unique_ids:
        row = by_id.get(pid)
        if row is None:
            continue
        description = _clean_description(row["description"])
        if description and len(description) > SHORT_DESCRIPTION_LENGTH:
            description = description[:SHORT_DESCRIPTION_LENGTH].rstrip() + "…"
        cards.append(ProductCard(
            product_id=row["product_id"],
            name=row["name"],
            price=row["price"],
            # Same URL scheme as the /api/products endpoint: /media/<file>.jpg
            image_url="/media/" + row["image_file_path"].removeprefix("products/"),
            garment_type=row["garment_type"],
            short_description=description,
        ))
    return cards
