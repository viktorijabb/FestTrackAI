# tests/integration/test_webhook.py
from fastapi.testclient import TestClient
from festtrackai.main import app
from festtrackai.db.database import init_db, get_all_festivals

client = TestClient(app)

def test_festival_ingestion_endpoint():
    """Tests that the webhook endpoint correctly validates and saves records to SQLite."""
    init_db()
    payload = [
        {
            "name": "Integration Test Fest",
            "fee": 12.00,
            "tier_deadline": "2026-10-06T00:00:00",
            "absolute_deadline": "2026-10-20T00:00:00"
        }
    ]

    response = client.post("/api/v1/festivals/ingest", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["saved_records"] == 1
    assert data["failed_records"] == 0

    festivals = get_all_festivals()
    assert any(f["name"] == "Integration Test Fest" for f in festivals)