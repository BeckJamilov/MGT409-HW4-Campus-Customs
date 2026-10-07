"""Customer memory (Problem 8): save and load logged-in customers' chats in chat_messages.

Table (already in the database):
    chat_messages(id, user_id, role, content, products_json, created_at)
- role is "user" or "assistant"
- products_json is NULL for user messages and a JSON list of product cards for assistant messages
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from pydantic import ValidationError
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from models import MAX_GUEST_HISTORY, ChatHistoryMessage, GuestHistoryMessage, ProductCard

HISTORY_FOR_AGENT = 20  # recent messages sent to the model as conversation context
HISTORY_FOR_PAGE = 50  # recent messages shown in the chat widget


def _connect(db_path: Path, read_only: bool = True) -> sqlite3.Connection:
    uri = f"file:{db_path.as_posix()}?mode={'ro' if read_only else 'rw'}"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _recent_rows(db_path: Path, user_id: int, limit: int) -> list[sqlite3.Row]:
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT role, content, products_json, created_at FROM chat_messages
            WHERE user_id = ? ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))  # oldest first


def _parse_products(products_json: str | None) -> list[ProductCard]:
    """Read saved product cards. Older rows use a richer format; take only the card fields."""
    if not products_json:
        return []
    cards = []
    try:
        items = json.loads(products_json)
    except json.JSONDecodeError:
        return []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        item = dict(item)
        if "short_description" not in item and isinstance(item.get("description"), str):
            item["short_description"] = item["description"][:110]
        # Older rows used /media/products/<file>; this app serves images at /media/<file>.
        if isinstance(item.get("image_url"), str):
            item["image_url"] = item["image_url"].replace("/media/products/", "/media/", 1)
        try:
            cards.append(ProductCard.model_validate(item))
        except ValidationError:
            continue
    return cards


def load_history_for_page(db_path: Path, user_id: int) -> list[ChatHistoryMessage]:
    return [
        ChatHistoryMessage(
            role=r["role"],
            content=r["content"],
            products=_parse_products(r["products_json"]),
            created_at=r["created_at"],
        )
        for r in _recent_rows(db_path, user_id, HISTORY_FOR_PAGE)
    ]


def _to_model_messages(items: list[tuple[str, str]]) -> list[ModelMessage]:
    """(role, text) pairs -> PydanticAI messages. The history must start with a customer message."""
    messages: list[ModelMessage] = []
    for role, text in items:
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=text)]))
        elif role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=text)]))
    while messages and isinstance(messages[0], ModelResponse):
        messages.pop(0)
    return messages


def load_history_for_agent(db_path: Path, user_id: int) -> list[ModelMessage]:
    """Convert saved rows into PydanticAI messages so the agent can continue the conversation."""
    items = []
    for r in _recent_rows(db_path, user_id, HISTORY_FOR_AGENT):
        text = r["content"]
        cards = _parse_products(r["products_json"]) if r["role"] == "assistant" else []
        if cards:
            # Remind the model which products it showed (ids only; details come from tools).
            text += "\n[Products shown on the page: " + ", ".join(c.product_id for c in cards) + "]"
        items.append((r["role"], text))
    return _to_model_messages(items)


def guest_history_for_agent(guest_history: list[GuestHistoryMessage]) -> list[ModelMessage]:
    """Problem 9: a guest's current-chat messages from the browser. Used for this request only;
    never written to the database."""
    return _to_model_messages([(m.role, m.content) for m in guest_history[-MAX_GUEST_HISTORY:]])


def save_exchange(
    db_path: Path, user_id: int, user_message: str, reply: str, products: list[ProductCard]
) -> None:
    """Save the customer's message and the assistant's reply in one transaction."""
    with closing(_connect(db_path, read_only=False)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
                (user_id, user_message),
            )
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
                (user_id, reply, json.dumps([p.model_dump() for p in products])),
            )
