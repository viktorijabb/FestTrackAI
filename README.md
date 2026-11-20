# FestTrackAI

FestTrackAI is a local-first, lightweight data ingestion and tracking pipeline designed for FilmFreeway film festival
records. It features a maintainable architecture that keeps data parsing and validation logic inside the Python codebase
rather than in visual workflow nodes.

## 🛠️ Tech Stack & Constraints

* **Backend**: FastAPI (Python) containerized with Docker
* **Database**: SQLite (`festivals.db`)
* **Scraping / Workflow**: n8n (acting as a simple HTTP scrape-and-forward relay)
* **Frontend**: Streamlit interactive dashboard
* **Resource Limit**: Optimized for low-memory execution within a **3.8 GiB RAM** budget.

---

## 🏗️ Architecture & Data Flow

1. **Scrape**: n8n fetches raw HTML content from target FilmFreeway pages.
2. **Relay**: n8n sends the raw HTML payload via HTTP POST to the FastAPI ingestion route (
   `/api/v1/festivals/ingest-html`).
3. **Deterministic Parsing**: FastAPI processes the payload with a Python parser (`src/festtrackai/scraper/parser.py`),
   extracting structured festival records from the embedded `application/ld+json` (`ItemList`) schema.
4. **Validation & Storage**: Pydantic models validate extracted records before committing them to SQLite.
5. **Visualization**: Streamlit reads directly from SQLite to present data in real time.

---

## 📁 Project Structure

```text
FestTrackAI/
├── src/festtrackai/
│   ├── main.py              # FastAPI app and database initialization
│   ├── api/routes.py        # Raw HTML ingestion endpoint
│   ├── db/database.py       # SQLite initialization, migration and upserts
│   ├── models/festival.py   # Pydantic validation
│   ├── scraper/parser.py    # JSON-LD extraction
│   └── app.py               # Streamlit table launched by Compose
├── workflows/festtrackai.json
├── Dockerfile
└── docker-compose.yml
```

---

## 🚀 Quick Start

1. **Build and launch containers**:
   ```bash
   docker compose up -d --build
   ```

2. **Access Endpoints**:
    * **FastAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
    * **Streamlit Dashboard**: [http://localhost:8501](http://localhost:8501)


## n8n HTML relay

Import `workflows/festtrackai.json` into n8n, select your existing ScraperAPI
credential on **Scrape**, and execute the manual trigger. The export intentionally
contains no credential references. It requires the same ScraperAPI community node
used by the previous workflow.

The flow is **Trigger → Scrape → Relay HTML → Send**. ScraperAPI rendering remains
on; autoparse is off because Python needs raw HTML. Relay HTML selects an HTML
string from `body`, `data`, `html`, `data.body`, or `data.html` without stripping
scripts or truncating the page. It stops with an actionable error if none exists.
If your community-node version uses a different envelope, inspect Scrape's output
and adjust only that field selection. Festival extraction stays in Python.

Send uses raw `text/html` and the exported expression `={{ $json.html }}`. The
leading `=` is required in exported n8n JSON; without it a template can be sent
literally. No LLM or item limit is needed: one HTML item can contain many festivals.
`http://app:8000` resolves between services in this Compose project. For n8n
running elsewhere, configure a reachable API address instead.

A 400 response means the HTML is empty, incorrectly forwarded, malformed, or
lacks the expected festival ItemList. Inspect Scrape output for a challenge/login
page. A parser change cannot restore metadata absent from the scraped response.

## Data semantics and repeat ingestion

The parser reads JSON-LD scripts regardless of attribute order, quote style, or
case, scans multiple scripts, and supports arrays, `@graph`, direct ItemList entries,
and local `@id` references. It rejects malformed or unresolved metadata instead of
silently reporting an incomplete import as successful.

FilmFreeway's directory metadata supplies festival names and **event dates**.
It does not establish submission fees or submission deadlines. Missing fees are
stored as SQL NULL (`None` in Python), not zero; missing submission deadlines are
`TBD`. `startDate` and ticket `offers.price` are deliberately not used for these
submission fields. Only explicit `fee` (USD), `tier_deadline`, and
`absolute_deadline` fields are mapped when supplied. Fetching festival detail pages
and extracting category-specific submission tiers is separate work.

On startup, FastAPI and Streamlit initialize the database. An automatic transaction
migrates the original NOT NULL fee column to nullable while retaining existing
IDs, names, fees, deadlines, and application statuses. Existing legacy zero fees
and dates cannot reliably be distinguished from genuine values and are retained;
review them rather than assuming this migration corrected historical data. Back
up `festivals.db` before upgrading; stop old app processes while migrating.

Re-ingestion matches the existing unique festival name, refreshes known fee and
deadline values, and preserves status and previously known fields when a new
listing supplies unknown values. This remains name-based identity: renames and
different festivals with identical names require a future stable source-ID model.

Responses distinguish `inserted_records` and `updated_records`; `saved_records`
is their sum (successful persistence operations, not necessarily changed values).
Mixed valid/invalid batches report `partial_success` and per-record validation
errors. All-invalid batches return 422; storage failures return 500 rather than a
misleading success. Earlier records may already be committed if storage fails
mid-batch; retrying is safe for festival identity and preserves application status.

Ollama is optional under the `ai` Compose profile and does not start by default:
`docker compose --profile ai up -d ollama`. The ingestion flow needs no local model.
The 3.8 GiB target has not been measured or enforced with container memory limits.

## Validation

With project dependencies installed:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_ingestion_regressions.py' -v
node --test tests/workflows/test_relay.cjs
uv run pytest
```

The first command uses Python's standard-library test runner. The Node tests
execute the exported relay code and body expression against representative scraper
envelopes; they do not launch a real n8n instance or call paid ScraperAPI endpoints.
The webhook tests use temporary databases and FastAPI's TestClient. The live
FilmFreeway listing checked during this fix contained 50 festival records; its
JSON-LD passed ingestion and repeat ingestion locally, with fees/deadlines unknown.

## FilmFreeway login and Gold submission prices

This is a **single-user local installation**. The app ports are bound to localhost;
do not expose this shared account session as a multi-user service.

1. On your desktop, from the project root (outside Docker), run:
   ```bash
   uv sync
   uv run playwright install chromium
   uv run python -m festtrackai.filmfreeway.account login --membership gold
   ```
   Use `--membership standard` for a non-Gold account. Membership is explicitly
   **user-confirmed**, not automatically verified. The public Gold festival badge
   and the presence of a Gold fee do not prove the account is a Gold member.
2. A visible browser opens FilmFreeway. Enter your credentials and complete any
   verification there. FestTrackAI never asks for or stores your password. The
   helper checks FilmFreeway's explicit sign-in marker on a fresh page, saves the
   session, and closes the browser. Closing it yourself cancels login; timeout is
   five minutes. Some identity providers may refuse automated Chromium; use a
   FilmFreeway-supported login method rather than bypassing account protections.
3. In Streamlit, open **FilmFreeway account & submission prices**, click **Check
   connection**, paste a festival profile URL, and **Refresh account prices**.
   When Streamlit runs directly on your desktop, **Sign in to FilmFreeway** launches
   the same helper. Docker cannot open a desktop window, so it displays the command.
   The existing project bind mount shares the session with the app container;
   the n8n container does not receive it.
4. Current category fees show Standard, Gold, the selected price and its basis,
   deadline when available, source URL, and fetch time. The budget filter uses the
   selected price. Gold uses the actual published Gold amount; no fixed discount
   is invented. Missing Gold prices fall back to Standard. Only verified USD
   metadata is used for numeric USD prices; other currencies remain visible as
   published text and are excluded from the USD budget filter.

Session state is in `.filmfreeway/session.json` (directory mode 0700, file mode
0600), excluded from Git and Docker builds. Only FilmFreeway cookies and origins
are saved, not Google or other provider sessions. This is a bearer credential:
do not upload, share, or copy it into n8n, Firecrawl, or ScraperAPI. The account
fetcher uses local Playwright directly, validates profile URLs, and checks sign-in
on every fetch. An expired session stops with a reconnect message instead of
silently returning anonymous prices.

**Disconnect FilmFreeway** (or
`uv run python -m festtrackai.filmfreeway.account disconnect`) removes local state
and clears displayed account prices on the next dashboard interaction. It does
not revoke sessions on FilmFreeway. Close any separately launched login helper
before disconnecting. Reconnect to switch accounts or update your confirmed
membership.

Prices stay in the current Streamlit session and do not overwrite the shared
SQLite listing fee. Refresh snapshots after membership, category, deadline, or
festival changes. The directory ingest remains an anonymous HTML relay. This
feature does not submit films or buy membership, and it does not bulk-fetch every
festival: paste a profile URL into the account pricing panel.

Validation command:
```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_filmfreeway_account.py' -v
```
The parser was exercised against a public festival page with 11 current categories.
The regression fixture below is a minimal public fee-table excerpt; session tests
use synthetic state. The execution environment disconnected before the new test
suite could run. A real signed-in Gold account, browser login, and Streamlit flow
still require local end-to-end verification.
