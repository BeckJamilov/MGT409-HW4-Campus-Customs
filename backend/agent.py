"""PydanticAI shopping agent for Campus Customs.

- System prompt: loaded from prompts/prompt.md
- Model: OpenAI through Portkey, key read from PORTKEY_API_KEY in the environment / .env
- Tools: find_products, filter_products, get_product_details, check_stock (tools.py)
- Output: AgentReply (text + product_ids), turned into ChatResponse with database-built cards
- Context: logged-in customer, current page, and saved chat history (Problem 8)
- Loop limits + audit trail of every run and tool call (Problem 12)
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from audit import append_event, new_run_id, redact
from models import AgentReply, ChatResponse
from tools import SHOP_TOOLS, ShopDeps, build_product_cards

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
DEFAULT_MODEL = "gpt-5.6-luna"

# Agent loop limits: one chat message may use at most this many model requests and tool calls.
MAX_MODEL_REQUESTS = 8
MAX_TOOL_CALLS = 12
MAX_RETRIES = 2  # retries per tool call / output validation after ModelRetry

SAFE_REFUSAL = (
    "Sorry, I can't help with that request. I'm happy to help you find Yale gear, check prices, "
    "or look up sizes and stock."
)

# Finds the nearest .env walking up from this file (the workspace .env holds PORTKEY_API_KEY).
load_dotenv(find_dotenv())


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def get_agent() -> Agent[ShopDeps, AgentReply]:
    """Build the agent once, on first use, so the rest of the API works even without a key."""
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing from .env")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
    )
    model = OpenAIChatModel(
        os.getenv("CHAT_MODEL", DEFAULT_MODEL),
        provider=OpenAIProvider(openai_client=client),
    )
    agent = Agent(
        model,
        deps_type=ShopDeps,
        output_type=AgentReply,
        instructions=load_system_prompt(),
        tools=SHOP_TOOLS,  # read-only product/price/stock lookups from tools.py
        retries=MAX_RETRIES,
    )

    @agent.instructions
    def customer_and_page_context(ctx: RunContext[ShopDeps]) -> str:
        """Per-request facts added after prompt.md: who is chatting and what page they're on."""
        lines = []
        customer = ctx.deps.customer
        if customer:
            lines.append(
                f"The customer is logged in. Name: {customer.name} "
                f"(first name: {customer.first_name or 'unknown'}). Email: {customer.email}. "
                "Earlier messages in this conversation are their saved chat history."
            )
        else:
            lines.append("The customer is a guest (not logged in). You don't know their name or email.")
        page = ctx.deps.page
        if page and page.product_id:
            lines.append(
                f"RIGHT NOW the customer is viewing the product page for '{page.product_name}' "
                f"(product_id: {page.product_id}). In their new message, 'this', 'it', or 'this one' "
                "means THIS product, even if earlier messages in the conversation were about a "
                "different product. Only use an earlier product if they name it explicitly."
            )
        elif page:
            lines.append(f"The customer is currently on the page {page.path}.")
        return "\n".join(lines)

    @agent.output_validator
    def only_products_from_tools(ctx: RunContext[ShopDeps], output: AgentReply) -> AgentReply:
        # Product cards may only come from real tool results, never from the model's memory.
        unknown = [pid for pid in output.product_ids if pid not in ctx.deps.seen_product_ids]
        if unknown:
            raise ModelRetry(
                f"These product_ids were not returned by a tool in this conversation: {unknown}. "
                "Only use product_ids from find_products, get_product_details, or check_stock results."
            )
        return output

    return agent


async def run_chat(
    message: str, deps: ShopDeps, history: list[ModelMessage] | None = None
) -> ChatResponse:
    """Run the agent once for a customer message, with loop limits and an audit trail."""
    deps.run_id = new_run_id()
    append_event({
        "event": "run_start",
        "run_id": deps.run_id,
        "customer": f"user:{deps.customer.user_id}" if deps.customer else "guest",
        "page_product_id": deps.page.product_id if deps.page else None,
        "history_messages": len(history or []),
        "message": redact(message),
    })
    limits = UsageLimits(request_limit=MAX_MODEL_REQUESTS, tool_calls_limit=MAX_TOOL_CALLS)
    try:
        result = await get_agent().run(
            message, deps=deps, message_history=history or None, usage_limits=limits
        )
    except UsageLimitExceeded as exc:
        append_event({"event": "run_end", "run_id": deps.run_id, "stop_reason": "usage_limit_exceeded",
                      "detail": redact(str(exc))})
        raise
    except ModelHTTPError as exc:
        if exc.status_code == 400 and "filter" in str(exc.body).lower():
            # The model provider's safety filter blocked the request (e.g. a jailbreak attempt).
            append_event({"event": "run_end", "run_id": deps.run_id, "stop_reason": "content_filter",
                          "detail": "Request blocked by the model provider's safety filter"})
            return ChatResponse(reply=SAFE_REFUSAL)
        append_event({"event": "run_end", "run_id": deps.run_id, "stop_reason": "error",
                      "detail": f"ModelHTTPError {exc.status_code}"})
        raise
    except Exception as exc:
        append_event({"event": "run_end", "run_id": deps.run_id, "stop_reason": "error",
                      "detail": f"{type(exc).__name__}: {redact(str(exc))}"})
        raise

    output = result.output
    cards = build_product_cards(deps, output.product_ids)
    end_event = {
        "event": "run_end",
        "run_id": deps.run_id,
        # The agent produced a validated AgentReply: the loop finished normally.
        "stop_reason": "final_output",
        "product_cards": len(cards),
        "reply": redact(output.reply),
    }
    try:
        usage = result.usage  # RunUsage (a property in this PydanticAI version)
        end_event.update({
            "model_finish_reason": result.response.finish_reason,
            "model": result.response.model_name,
            "requests": usage.requests,
            "tool_calls": usage.tool_calls,
            "tokens": {"input": usage.input_tokens, "output": usage.output_tokens},
        })
    except Exception:  # extra details are optional; never fail the customer's reply over logging
        pass
    append_event(end_event)
    return ChatResponse(reply=output.reply, products=cards)
