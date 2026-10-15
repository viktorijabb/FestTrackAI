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
├── src/
│   └── festtrackai/
│       ├── api/
│       │   └── routers/
│       │       └── festivals.py  # FastAPI ingestion endpoint
│       ├── db/
│       │   └── database.py       # SQLite schema & persistence helpers
│       ├── models/
│       │   └── festival.py       # Pydantic validation models
│       └── scraper/
│           └── parser.py         # JSON-LD HTML parser service
├── app.py                        # Streamlit dashboard UI
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