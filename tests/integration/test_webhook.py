from fastapi.testclient import TestClient
from festtrackai.api.routes import app
from festtrackai.db.database import init_db, get_all_festivals

client = TestClient(app)

def and_clear_db():
    init_db()

def test_festival_ingestion_endpoint():
    """Tests that the webhook endpoint correctly validates and saves records to SQLite."""
    payload = [
        {
            "name": "Integration Test Fest",
            "fee": 12.00,
            "tier_deadline": "10/06/2026",
            "absolute_deadline": "20/06/2026"
        }
    ]

    response = client.post("/api/v1/festivals/ingest", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["saved_records"] == 1
    assert data["failed_records"] == 0

    # Verify it actually made it into the SQLite database
    festivals = get_all_festivals()
    assert any(f["name"] == "Integration Test Fest" for f in festivals)