# Campus Customs: MGT 409 Homework 4

A Campus Customs (Yale Bulldog Blue) storefront with an AI shopping assistant.

- **Frontend:** React + Vite + TypeScript (`frontend/`)
- **Backend:** FastAPI (`backend/main.py`) with a PydanticAI agent (`backend/agent.py`)
  - read-only database tools (`backend/tools.py`)
  - structured models (`backend/models.py`)
  - system prompt (`backend/prompts/prompt.md`)
- **Data:** SQLite catalogue, inventory, users, and chat history (`data/campus_customs.db`) plus product photos (`data/products/`)

Full documentation of how the system works is in [`output/harness.md`](output/harness.md).

## Requirements

- Python 3.12 or newer
- Node.js 20 or newer (includes `npm`)
- A Portkey API key (used to call the OpenAI model `gpt-5.6-luna`)

## 1. Add the provided data pack

The database and product images are **not in this repository**. Copy them from the course data pack into the `data/` folder so it looks like this:

```
data/
  campus_customs.db
  products/
    2025-yale-vs-harvard-t-shirt.jpg
    ... (102 .jpg files)
```

## 2. Create the Python environment and install requirements

From the project root (the folder with this README):

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Set environment variables

Copy the example file and put your own key in it:

```bash
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env` instead.

Then edit `.env`:

```
PORTKEY_API_KEY=your-portkey-api-key-here        # required for the chat assistant
SESSION_SECRET=any-long-random-string            # optional: keeps logins valid across restarts
CHAT_MODEL=gpt-5.6-luna                          # optional: model name
```

The backend loads `.env` automatically. Never commit `.env`; it is listed in `.gitignore`.

## 4. Run the backend (port 8000)

With the virtual environment activated:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Check it: http://localhost:8000/api/health should return `{"status":"ok"}`.

## 5. Install and run the frontend (port 5173)

In a **second terminal**, from the project root:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server forwards `/api` and `/media` requests to the backend on port 8000, so both must be running.

## Test login

| Email | Password |
|---|---|
| `test@campuscustoms.yale.edu` | `password` |

You can also create a new account on the **Create account** page.

## Things to try

- **Products page:** filter by category and in-stock size, and sort by price. Click a product for stock per size.
- **Chat (bottom right):**
  - "what hoodies do you have?" (product cards appear on the page)
  - "Do you have the Baseball Left Chest Crewneck in XS?" (real stock from the database)
  - "cheapest fleece"
  - on a product page: "do you have this in M?"
- **Memory:** log in, chat, refresh the page, and your conversation is restored.

## Homework deliverables

| File | Contents |
|---|---|
| `AI_prompts.md` | Prompt log for Problems 1–13 |
| `output/harness.md` | Database analysis and full system documentation (models, tools, safety, specs, how to run) |
| `output/usability.md` | Usability improvements (Problem 9) |
| `output/design.md` | Design changes (Problem 10) |
| `output/app_check.html` + `output/app_check_images/` | Live app test with screenshots (Problem 11). Open by double-click |
| `output/audit_trail.json` | Append-only audit trail of agent runs and tool calls (Problem 12) |

## Project structure

```
backend/
  main.py            FastAPI app: products, images, login/signup, chat, chat history
  agent.py           PydanticAI agent: model, prompt, context, loop limits, audit
  tools.py           read-only database tools (search, filter, details, stock)
  models.py          Pydantic request/response and tool-result models
  memory.py          saved chat history (logged in) and guest chat context
  audit.py           append-only audit trail with redaction
  prompts/prompt.md  system prompt: voice, tool rules, safety rules
frontend/            React + Vite + TypeScript app
data/                data pack goes here (not committed)
output/              homework deliverables
requirements.txt     Python packages
.env.example         environment variable template
```
