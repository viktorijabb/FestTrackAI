"""The webhook accepts raw HTML, not the retired /ingest JSON route."""
import json
from fastapi.testclient import TestClient
from festtrackai.main import app
from festtrackai.db.database import get_all_festivals


def test_festival_ingestion_endpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    html = '<script type="application/ld+json">' + json.dumps({
        "@type": "ItemList", "itemListElement": [{"item": {
            "name": "Integration Test Fest", "fee": 12,
            "tier_deadline": "2026-10-06", "absolute_deadline": "2026-10-20"
        }}]
    }) + '</script>'
    with TestClient(app) as client:
        response = client.post("/api/v1/festivals/ingest-html", content=html,
                               headers={"Content-Type": "text/html"})
    assert response.status_code == 200
    assert response.json()["inserted_records"] == 1
    assert get_all_festivals()[0]["fee"] == 12
