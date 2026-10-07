# Campus Customs: Usability Improvements (Problem 9)

Four improvements were planned before any code was changed. Each one builds on what already exists (catalogue API, chat agent, database tools, saved history) and does not change the overall site design.

---

## 1. Product filters and sorting (frontend)

**What it adds:** The Products page gets three controls next to the existing search box:
- a **category** filter (T-Shirts, Hoodies, Crewnecks & Sweatshirts, Quarter-Zips, Jackets & Fleece, Long Sleeve & Performance);
- an **in-stock size** filter (XS–XXL), which shows only products that actually have that size in stock;
- **sorting**: name, price low → high, price high → low.

A "Clear filters" button resets everything.

- The category comes from the database's `garment_type`. The backend groups the 22 inconsistent spellings ("short-sleeve T-shirt", "t-shirt", …) into 6 clean categories.
- The size filter uses real `inventory` quantities, which the `/api/products` list now includes.

**Why it helps:**
- **Shopper:** 102 products is a lot to scroll. A shopper who wears XL and wants a hoodie can see just the hoodies they can actually buy, in two clicks, and can sort by price to match a budget.
- **Business:** fewer "do you have this in my size?" dead ends, less frustration with sold-out items, and a faster path to purchase.

## 2. Quick suggestion buttons in chat (frontend)

**What it adds:** A row of one-click suggestion buttons above the chat input:
- **"Show me hoodies"**
- **"Gift ideas under $50"**
- **"Cheapest fleece"**
- on a product page only: **"Is this in stock in M?"**, which uses the existing page context

Clicking a button sends that message to the assistant.

**Why it helps:**
- **Shopper:** many people don't know what a shop chatbot can do or how to phrase a question. Buttons show what's possible (search, stock, gifts, prices) and save typing, especially on mobile.
- **Business:** more people try the assistant, and each button leads straight to product cards, so it drives browsing and sales.

## 3. Short-term conversation context for guests (agent/backend)

**What it adds:**
- While a guest is chatting, the chat widget sends the last few messages of the **current** conversation with each new message, and the agent gets them as conversation history.
- This makes follow-ups work: "what hoodies do you have?" → "which of those is cheapest?" or "do you have the first one in M?"
- **Nothing is written to `chat_messages` for guests.** The context lives only in the open browser tab and is gone on refresh or close.
- Logged-in customers keep using their saved history from the database, as in Problem 8.

**Why it helps:**
- **Shopper:** a conversation that forgets the previous question feels broken. Guests can now have a natural back-and-forth without being forced to create an account.
- **Business:** better first impressions for new visitors, who are often guests, with no new storage of personal data for people who haven't signed up.

## 4. Filtered product lookup tool (agent/backend)

**What it adds:** A new database tool, `filter_products`, that the agent uses for questions with conditions. It filters on:
- category;
- keywords;
- minimum and maximum price;
- a size that must be in stock.

It can sort by price (low → high or high → low) or by name, and it returns real products with their real prices and in-stock sizes.

| Question | Tool call |
|---|---|
| "hoodies under $70" | category = hoodies, max price = 70 |
| "cheapest fleece" | keywords = fleece, sorted by price low → high |
| "crewnecks in XL" | category = crewnecks, size = XL |

The results become product cards on the page through the existing Problem 7 flow.

**Why it helps:**
- **Shopper:** answers budget and size questions accurately in one step, instead of the agent searching broadly and estimating.
- **Business:** price and stock answers always come from SQL filtering of the live database, never from the model's guesses, so customers aren't promised items that are too expensive or out of stock. "Cheapest" and "under $X" questions are common buying signals, and they now get exact answers.

---

## Implementation summary

| # | Where | What changed |
|---|---|---|
| 1 | `backend/tools.py` `category_for()`, `backend/main.py` `/api/products`; `frontend/src/pages/Products.tsx` | Each product now has a `category` (6 groups covering all 102 products) and `sizes_in_stock` (from `inventory`, quantity > 0). The Products page has Category, "Size in stock", and "Sort by" dropdowns plus "Clear filters". Chat results view is unchanged. |
| 2 | `frontend/src/components/ChatWidget.tsx` | A row of suggestion buttons above the input: "Show me hoodies", "Gift ideas under $50", "Cheapest fleece". On a product page the first one becomes "Is this in stock in M?". Clicking a button sends that message through the normal chat flow. |
| 3 | `ChatWidget.tsx`, `backend/models.py` (`GuestHistoryMessage`, `ChatRequest.guest_history`), `backend/memory.py` (`guest_history_for_agent`), `backend/main.py` | Guests' last 12 messages of the current chat are sent with each request. Assistant messages include a note listing the product_ids from the API response. The backend turns them into PydanticAI message history for that request only, and **never saves them**. Logged-in users ignore this field and use saved history. |
| 4 | `backend/tools.py` `filter_products`, `backend/models.py` (`FilteredProduct`, `FilteredProductsResult`), `backend/prompts/prompt.md` | New tool with category, keywords, min/max price, in-stock size, sort, and limit. Price and size filtering runs in SQL; results return real prices, in-stock sizes, and the quantity in the requested size. Returned ids can become page cards through the existing Problem 7 flow. |

**Bug found and fixed during testing:** on a product page, a logged-in customer with older saved history asked "Is this in stock in M?". The agent answered about the product from the *earlier* conversation (Ice Hockey hoodie) instead of the page they were on (Basic Hoodie Big Yale). The page-context instruction in `agent.py` and `prompt.md` now says the page open **right now** takes priority over earlier messages. The retest answered about the right product.

## Test results (running app, 2026-10-06)

| # | Test | Result |
|---|---|---|
| 1 | Products page: Category = Hoodies, Size in stock = XL, Sort = price low → high | "21 of 102 items". Prices ascending ($45 → $88). The 21 product ids are **exactly** the set from SQL (hood-type products with XL quantity > 0) |
| 1 | "Clear filters" | Back to 102 of 102; button hidden |
| 2 | Chat suggestion buttons (general pages) | "Show me hoodies", "Gift ideas under $50", "Cheapest fleece" shown and clickable |
| 2 | Product page buttons | "Is this in stock in M?" appears first; on Basic Hoodie Big Yale it answered "in stock in size M, with 5 units" (database: M = 5) and stayed on the page |
| 2+4 | Click "Cheapest fleece" | "The cheapest fleece match is School Of Art 1 4 Zip at $72.00. There are 8 fleece matches total…" + 3 cards ($72, $98, $98), the same order as SQL. "8 total" is `filter_products`' count (keyword search alone finds 7) |
| 3+4 | Guest: "Show me hoodies" → "Which of those are under $50?" | "Two hoodies are under $50, both priced at $45.00: Ua Gameday Double Knit Hood and Yale Sports Hoodie Tennis" + 2 cards (matches SQL) |
| 3 | Guest follow-up: "Is the tennis one available in medium?" | "Yes… available in medium, with 25 in stock" (database: 25) |
| 3 | Guest messages saved? | `chat_messages` stayed at **32 rows** during all guest tests: not saved |
| 3 | Guest refreshes the page, then asks "Which of those are under $50?" | Chat reset; the agent no longer knew "those" meant hoodies (answered for all 30 products ≤ $50). Context lived only in the current chat |
| – | Logged-in regression (Handsome Dan) | Saved history restored in the widget; new messages saved (rows 33–36); page context and product cards still work |
