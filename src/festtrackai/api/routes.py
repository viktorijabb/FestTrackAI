import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError
from festtrackai.models.festival import Festival
from festtrackai.db.database import insert_festival
from festtrackai.scraper.parser import parse_filmfreeway_html

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/festivals", tags=["festivals"])


@router.post("/ingest-html")
async def ingest_html_festivals(request: Request):
    """Receive intact HTML; parsing and validation live entirely in Python."""
    try:
        html_content = (await request.body()).decode("utf-8-sig")
        raw_festivals = parse_filmfreeway_html(html_content)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"HTML parsing failed: {exc}") from exc

    counts = {"inserted": 0, "updated": 0}
    errors = []
    for index, item in enumerate(raw_festivals):
        try:
            fee = item.get("fee")
            if isinstance(fee, str):
                # The model stores USD only; do not silently relabel GBP/EUR.
                fee = fee.removeprefix("$").strip()
                fee = float(fee) if fee else None
            validated = Festival(**{**item, "fee": fee})
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append({"index": index, "error": str(exc)})
            continue
        try:
            counts[insert_festival(validated.model_dump())] += 1
        except Exception as exc:
            logger.exception("Festival persistence failed")
            raise HTTPException(status_code=500, detail="Festival persistence failed; check API logs.") from exc
    saved = sum(counts.values())
    status = "partial_success" if errors and saved else "error" if errors else "success"
    result = {
        "status": status, "parsed_records": len(raw_festivals),
        "saved_records": saved, "inserted_records": counts["inserted"],
        "updated_records": counts["updated"], "failed_records": len(errors),
        "errors": errors,
    }
    if errors and not saved:
        raise HTTPException(status_code=422, detail=result)
    return result
