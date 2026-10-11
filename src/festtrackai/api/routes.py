from fastapi import FastAPI, HTTPException
from festtrackai.models.festival import Festival
from festtrackai.db.database import init_db, insert_festival
from pydantic import ValidationError

app = FastAPI(title="FestTrackAI Webhook API")

# Initialize database schema on API startup
init_db()

@app.post("/api/v1/festivals/ingest")
async def ingest_festivals(payload: list[dict]):
    """Webhook endpoint to receive scraped festival records from n8n."""
    saved_count = 0
    errors = []

    for item in payload:
        try:
            # Enforce validation using our existing Pydantic model
            validated_festival = Festival(
                name=item.get("name", ""),
                fee=float(item.get("fee", 0.0)),
                tier_deadline=str(item.get("tier_deadline", "TBD")),
                absolute_deadline=str(item.get("absolute_deadline", "TBD")),
                status="Unapplied"
            )
            # Insert validated record into SQLite database
            insert_festival(validated_festival.model_dump())
            saved_count += 1
        except ValidationError as ve:
            errors.append({"item": item, "error": str(ve)})
        except Exception as e:
            errors.append({"item": item, "error": str(e)})

    return {
        "status": "success",
        "saved_records": saved_count,
        "failed_records": len(errors),
        "errors": errors
    }