"""Append-only audit trail of agent activity (Problem 12).

File: output/audit_trail.json, a JSON array of event objects:
    run_start  -> who (guest / user id), page, short redacted message preview
    tool_call  -> tool name, short arguments, short result, status, duration
    run_end    -> stop reason, model finish reason, requests/tool calls used, cards returned

Append-only: existing bytes are never rewritten. A new entry is written over the closing "]"
of the array, followed by a new "]", so the file stays valid JSON and old entries stay intact.
Nothing secret is logged: no API keys, passwords, tokens, or emails; long digit runs (card
numbers) are masked, and all text is truncated.
"""

import functools
import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_TEXT = 120  # characters kept from any logged string
MAX_ITEMS = 5  # list items kept in result summaries

_lock = threading.Lock()
logger = logging.getLogger("campus_customs.audit")

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")  # 13–19 digits, optional spaces/dashes
_SECRET_WORDS = re.compile(r"(?i)\b(password|passcode|pwd|api[_ -]?key|token|secret)\b\s*[:=]?\s*\S+")


def redact(text: str, limit: int = MAX_TEXT) -> str:
    """Mask sensitive-looking content and shorten."""
    text = _CARD.sub("[card number removed]", text)
    text = _EMAIL.sub("[email]", text)
    text = _SECRET_WORDS.sub(lambda m: f"{m.group(1)} [removed]", text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_event(event: dict[str, Any]) -> None:
    """Append one event to the JSON array without rewriting earlier entries."""
    entry = json.dumps({"time": _now(), **event}, ensure_ascii=False)
    with _lock:
        try:
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
                with open(AUDIT_PATH, "x" if not AUDIT_PATH.exists() else "a", encoding="utf-8") as f:
                    f.write("[\n" + entry + "\n]\n")
                return
            with open(AUDIT_PATH, "r+b") as f:
                # Find the closing "]" at the end of the file (skipping trailing whitespace).
                f.seek(0, 2)
                pos = f.tell()
                while pos > 0:
                    pos -= 1
                    f.seek(pos)
                    ch = f.read(1)
                    if not ch.isspace():
                        break
                if ch != b"]":
                    # Never truncate a file we don't understand; keep old content untouched.
                    logger.error("Audit file does not end with ']'; entry not written")
                    return
                f.seek(pos)
                f.write((",\n" + entry + "\n]\n").encode("utf-8"))
        except OSError:
            logger.exception("Could not write audit entry")


# ---------------------------------------------------------------------------
# Short, safe summaries of tool arguments and results
# ---------------------------------------------------------------------------


def _short_args(kwargs: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        out[key] = redact(value, 60) if isinstance(value, str) else value
    return out


def summarize_result(result: Any) -> str:
    """One short line describing a tool result (counts, ids, prices, stock), never full records."""
    if not isinstance(result, BaseModel):
        return redact(str(result))
    data = result.model_dump()
    if "matches" in data:  # ProductSearchResult
        ids = [m["product_id"] for m in data["matches"]]
        more = f" (+{len(ids) - MAX_ITEMS} more)" if len(ids) > MAX_ITEMS else ""
        return f"{len(ids)} shown of {data['total_matches']}: {', '.join(ids[:MAX_ITEMS])}{more}"
    if "products" in data and "filters" in data:  # FilteredProductsResult
        items = [f"{p['product_id']} ${p['price']:.0f}" for p in data["products"]]
        more = f" (+{len(items) - MAX_ITEMS} more)" if len(items) > MAX_ITEMS else ""
        return f"{len(items)} shown of {data['total_matches']}: {', '.join(items[:MAX_ITEMS])}{more}"
    if "status" in data:  # StockCheckResult
        return f"{data['product_id']} ${data['price']:.2f}: {data['status']}"
    if "sizes_in_stock" in data:  # ProductDetails
        return (f"{data['product_id']} ${data['price']:.2f}, total stock {data['total_stock']}, "
                f"in stock: {','.join(data['sizes_in_stock']) or 'none'}")
    return redact(json.dumps(data, default=str))


def audited_tool(func):
    """Wrap an agent tool so every call is recorded (name, short args, short result, status).

    functools.wraps keeps the name, docstring, and signature, so PydanticAI still builds the
    same tool schema for the model.
    """

    @functools.wraps(func)
    def wrapper(ctx, *args, **kwargs):
        start = time.perf_counter()
        run_id = getattr(ctx.deps, "run_id", None)
        event = {"event": "tool_call", "run_id": run_id, "tool": func.__name__, "args": _short_args(kwargs)}
        try:
            result = func(ctx, *args, **kwargs)
        except Exception as exc:  # includes ModelRetry (the model is asked to fix its call)
            append_event({**event, "status": "retry" if type(exc).__name__ == "ModelRetry" else "error",
                          "result": redact(str(exc)),
                          "duration_ms": round((time.perf_counter() - start) * 1000)})
            raise
        append_event({**event, "status": "ok", "result": summarize_result(result),
                      "duration_ms": round((time.perf_counter() - start) * 1000)})
        return result

    return wrapper
