"""Pydantic models for the chat API."""

from typing import Literal

from pydantic import BaseModel, Field

MAX_MESSAGE_LENGTH = 2000


class ProductCard(BaseModel):
    """A product shown as a card on the page. Built by the backend from the database."""

    product_id: str
    name: str
    price: float
    image_url: str
    garment_type: str | None = None
    short_description: str | None = None


class PageContext(BaseModel):
    """Where the customer is on the website when they send a message (Problem 8)."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(
        default=None,
        max_length=200,
        description="product_id from the URL when the customer is on a single product page.",
    )


MAX_GUEST_HISTORY = 12


class GuestHistoryMessage(BaseModel):
    """One earlier message of a guest's current chat, sent by the browser (Problem 9)."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    """What the frontend sends: one customer message plus the current page."""

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    page_context: PageContext | None = None
    # Guests only: recent messages of the current chat (kept in the browser, never saved).
    guest_history: list[GuestHistoryMessage] = Field(default_factory=list, max_length=MAX_GUEST_HISTORY)


class ChatResponse(BaseModel):
    """What the frontend receives: the agent's reply plus any product cards to display."""

    reply: str
    products: list[ProductCard] = Field(default_factory=list)


class ChatHistoryMessage(BaseModel):
    """One saved chat message returned to the frontend (Problem 8)."""

    role: str
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryMessage]


class AgentReply(BaseModel):
    """Structured output of the agent (Problem 7).

    The agent only picks product_ids; the backend turns them into ProductCards from the
    database, so names, prices, and images can never be invented by the model.
    """

    reply: str = Field(description="The text answer shown in the chat bubble.")
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "product_ids (from tool results in this conversation) to show as product cards on "
            "the page, in display order. Empty when no products should be shown."
        ),
    )


# ---------------------------------------------------------------------------
# Problem 6: results returned by the database tools to the agent
# ---------------------------------------------------------------------------


class ProductMatch(BaseModel):
    """One search hit: just enough for the agent to pick the right product_id."""

    product_id: str
    name: str
    garment_type: str
    price: float


class ProductSearchResult(BaseModel):
    query: str
    matches: list[ProductMatch]
    total_matches: int


class SizeStock(BaseModel):
    size: str
    quantity: int
    in_stock: bool


class ProductDetails(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str | None = Field(
        description="Product description from the catalogue, or null if none is on file."
    )
    colors: list[str]
    price: float
    sizes: list[SizeStock]
    total_stock: int
    sizes_in_stock: list[str]
    sizes_out_of_stock: list[str]


class FilteredProduct(BaseModel):
    """One result of filter_products (Problem 9)."""

    product_id: str
    name: str
    category: str
    garment_type: str
    price: float
    sizes_in_stock: list[str]
    quantity_in_requested_size: int | None = Field(
        default=None, description="Units in stock for the size filter, if one was given."
    )


class FilteredProductsResult(BaseModel):
    filters: dict = Field(description="The filters that were applied.")
    products: list[FilteredProduct]
    total_matches: int


class StockCheckResult(BaseModel):
    product_id: str
    name: str
    price: float
    requested_size: str | None = Field(description="Normalized size asked about, or null for all sizes.")
    quantity: int | None = Field(description="Units in stock for the requested size (null if no size asked).")
    in_stock: bool | None = Field(description="Whether the requested size is available (null if no size asked).")
    status: str = Field(description="Plain-language summary, e.g. 'M is out of stock'.")
    sizes: list[SizeStock]
    total_stock: int
