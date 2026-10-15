from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError
from festtrackai.models.festival import Festival
from festtrackai.db.database import insert_festival
from festtrackai.scraper.parser import parse_filmfreeway_html

router = APIRouter(prefix="/api/v1/festivals", tags=["festivals"])

class HtmlPayload(BaseModel):
    """Pydantic model defining the expected raw HTML body request."""
    body: str

@router.post("/ingest-html")
async def ingest_html_festivals(payload: HtmlPayload):
    """
    Receives raw HTML, extracts festival records using the JSON-LD parser[cite: 1],
    validates them against the Festival model, and saves them to SQLite.
    """
    try:
        # 1. Extract raw festival records from HTML metadata
        raw_festivals = parse_filmfreeway_html(payload.body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"HTML parsing failed: {str(e)}")

    saved_count = 0
    errors = []

    # 2. Iterate through records, validate with Pydantic, and insert into DB
    for item in raw_festivals:
        try:
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
        "parsed_records": len(raw_festivals),
        "saved_records": saved_count,
        "failed_records": len(errors),
        "errors": errors
    }