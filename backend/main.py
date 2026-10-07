"""Campus Customs backend.

- Problem 3: read-only API for the product catalogue, inventory, and product images
  from data/campus_customs.db and data/products/.
- Problem 4: create account / log in using the users table.
- Problem 5: /api/chat endpoint backed by the PydanticAI agent (agent.py).
- Problem 8: customer memory (memory.py) and page context for chat.

Run from the backend folder (with the project's .venv activated):
    uvicorn main:app --reload --port 8000
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import run_chat
from memory import guest_history_for_agent, load_history_for_agent, load_history_for_page, save_exchange
from models import ChatHistoryResponse, ChatRequest, ChatResponse, PageContext
from tools import CurrentPage, Customer, ShopDeps, category_for

logger = logging.getLogger("campus_customs")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

app = FastAPI(title="Campus Customs API")

# Allow the Vite dev server to call the API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Product images: catalogue.image_file_path "products/x.jpg" -> /media/x.jpg
app.mount("/media", StaticFiles(directory=DATA_DIR / "products"), name="media")


def get_connection() -> sqlite3.Connection:
    """Open the database read-only (used for all reads; only signup writes)."""
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def product_from_row(row: sqlite3.Row) -> dict:
    """Turn a catalogue row into JSON-friendly data (colors/tags are stored as JSON text)."""
    image_path = row["image_file_path"]  # e.g. "products/basic-hoodie-big-yale.jpg"
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "category": category_for(row["garment_type"]),
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "image_url": "/media/" + image_path.removeprefix("products/"),
        "price": row["price"],
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def list_products() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
                   GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_in_stock
            FROM catalogue c
            LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
    return [
        {
            **product_from_row(r),
            "total_stock": r["total_stock"],
            # Problem 9: lets the Products page filter by sizes that are actually in stock.
            "sizes_in_stock": sorted(
                (r["sizes_in_stock"] or "").split(",") if r["sizes_in_stock"] else [],
                key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else 99,
            ),
        }
        for r in rows
    ]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock_rows = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    inventory = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock_rows),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99,
    )
    return {
        **product_from_row(row),
        "inventory": inventory,
        "total_stock": sum(s["quantity"] for s in inventory),
    }


# ---------------------------------------------------------------------------
# Problem 4: authentication
# ---------------------------------------------------------------------------

# Matches the hashes already in the users table: "pbkdf2_sha256$<salt>$<hex digest>",
# PBKDF2-HMAC-SHA256 with 120,000 iterations and the salt text used as UTF-8 bytes.
PBKDF2_ITERATIONS = 120_000
MIN_PASSWORD_LENGTH = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SESSION_SECONDS = 7 * 24 * 60 * 60

# Secret used to sign login tokens. Set SESSION_SECRET in the environment to keep users
# logged in across server restarts; otherwise a random secret is generated at startup.
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)


def get_write_connection() -> sqlite3.Connection:
    """Read/write connection, used only for creating user accounts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, _ = stored_hash.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    # Constant-time comparison avoids leaking how many characters matched.
    return hmac.compare_digest(hash_password(password, salt), stored_hash)


def sign(payload: str) -> str:
    signature = hmac.new(SESSION_SECRET.encode(), payload.encode(), "sha256").digest()
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def create_token(user_id: int) -> str:
    """Signed token "<user_id>.<expiry>.<signature>" so the frontend can stay logged in."""
    payload = f"{user_id}.{int(time.time()) + SESSION_SECONDS}"
    return f"{payload}.{sign(payload)}"


def user_id_from_token(token: str) -> int | None:
    try:
        user_id, expiry, signature = token.split(".")
        if not hmac.compare_digest(signature, sign(f"{user_id}.{expiry}")) or int(expiry) < time.time():
            return None
        return int(user_id)
    except ValueError:
        return None


def public_user(row: sqlite3.Row) -> dict:
    """User fields that are safe to send to the browser (never the password hash)."""
    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "name": row["name"],
        "email": row["email"],
    }


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/signup", status_code=201)
def signup(body: SignupRequest) -> dict:
    first_name = body.first_name.strip()
    last_name = body.last_name.strip()
    email = body.email.strip().lower()

    if not first_name or not last_name:
        raise HTTPException(status_code=400, detail="First and last name are required.")
    if len(first_name) > 50 or len(last_name) > 50:
        raise HTTPException(status_code=400, detail="Names must be 50 characters or fewer.")
    if not EMAIL_PATTERN.match(email) or len(email) > 254:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    with closing(get_write_connection()) as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        try:
            with conn:  # commits on success, rolls back on error
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash, first_name, last_name)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (f"{first_name} {last_name}", email, hash_password(body.password), first_name, last_name),
                )
        except sqlite3.IntegrityError:  # UNIQUE(email) safety net
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return {"user": public_user(row)}


@app.post("/api/auth/login")
def login(body: LoginRequest) -> dict:
    email = body.email.strip().lower()
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    # Same message for unknown email and wrong password, so emails can't be probed.
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return {"user": public_user(row), "token": create_token(row["id"])}


def user_from_authorization(authorization: str) -> sqlite3.Row | None:
    """Return the users row for a "Bearer <token>" header, or None if missing/invalid."""
    user_id = user_id_from_token(authorization.removeprefix("Bearer ").strip())
    if user_id is None:
        return None
    with closing(get_connection()) as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.get("/api/auth/me")
def me(authorization: str = Header(default="")) -> dict:
    row = user_from_authorization(authorization)
    if row is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return {"user": public_user(row)}


# ---------------------------------------------------------------------------
# Problem 5: chat with the PydanticAI agent
# ---------------------------------------------------------------------------


def customer_from_row(row: sqlite3.Row) -> Customer:
    return Customer(
        user_id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        name=row["name"],
        email=row["email"],
    )


def current_page(context: PageContext | None) -> CurrentPage | None:
    """Trust only the product_id from the frontend; look up the product name in the database."""
    if context is None:
        return None
    page = CurrentPage(path=context.path)
    if context.product_id:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT product_id, name FROM catalogue WHERE product_id = ?", (context.product_id,)
            ).fetchone()
        if row:  # unknown ids are ignored
            page.product_id, page.product_name = row["product_id"], row["name"]
    return page


@app.post("/api/chat")
async def chat(body: ChatRequest, authorization: str = Header(default="")) -> ChatResponse:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Logged-in customers get memory; guests can chat but nothing is saved.
    user = user_from_authorization(authorization)
    customer = customer_from_row(user) if user else None
    deps = ShopDeps(db_path=DB_PATH, customer=customer, page=current_page(body.page_context))
    if deps.page and deps.page.product_id:
        # The product on screen is verified, so the agent may show it as a card.
        deps.seen_product_ids.add(deps.page.product_id)
    # Logged in: saved history from chat_messages. Guest: current-chat messages from the
    # browser (Problem 9), used for this request only and never saved.
    if customer:
        history = load_history_for_agent(DB_PATH, customer.user_id)
    else:
        history = guest_history_for_agent(body.guest_history)

    try:
        response = await run_chat(message, deps, history)
    except Exception:
        # Log details on the server only; never send internal errors (or keys) to the browser.
        logger.exception("Chat agent failed")
        raise HTTPException(
            status_code=502, detail="The assistant is unavailable right now. Please try again."
        )

    if customer:
        save_exchange(DB_PATH, customer.user_id, message, response.reply, response.products)
    return response


@app.get("/api/chat/history")
def chat_history(authorization: str = Header(default="")) -> ChatHistoryResponse:
    """Saved conversation for the logged-in customer, oldest first."""
    user = user_from_authorization(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Log in to see your chat history.")
    return ChatHistoryResponse(messages=load_history_for_page(DB_PATH, user["id"]))
