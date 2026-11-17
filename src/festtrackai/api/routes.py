from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError
from festtrackai.models.festival import Festival
from festtrackai.db.database import insert_festival
from festtrackai.scraper.parser import parse_filmfreeway_html

router = APIRouter(prefix="/api/v1/festivals", tags=["festivals"])

@router.post("/ingest-html")
async def ingest_html_festivals(request: Request):
    """
    Receives raw HTML directly from n8n, extracts festival records using JSON-LD,
    validates them against the Festival model, and saves them to SQLite.
    """
    try:
        # Read raw body bytes directly from the request
        body_bytes = await request.body()
        html_content = body_bytes.decode("utf-8")

        # 1. Extract raw festival records from HTML metadata
        raw_festivals = parse_filmfreeway_html(html_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"HTML parsing failed: {str(e)}")

    saved_count = 0
    errors = []

    # 2. Iterate through records, validate with Pydantic, and insert into DB
    for item in raw_festivals:
        try:
            # Safe fee parsing helper
            fee_raw = item.get("fee", 0.0)
            if isinstance(fee_raw, str):
                cleaned_fee = fee_raw.replace("$", "").replace("£", "").replace("€", "").strip()
                fee_val = float(cleaned_fee) if cleaned_fee else 0.0
            else:
                fee_val = float(fee_raw or 0.0)

            validated_festival = Festival(
                name=item.get("name", ""),
                fee=fee_val,
                tier_deadline=str(item.get("tier_deadline", "TBD")),
                absolute_deadline=str(item.get("absolute_deadline", "TBD")),
                status="Unapplied"
            )

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