import json
import re
from typing import List, Dict, Any

def parse_filmfreeway_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses raw FilmFreeway HTML to extract festival records from the embedded
    JSON-LD ItemList schema[cite: 1].

    Args:
        html_content (str): The raw HTML string fetched from the scraper.

    Returns:
        List[Dict[str, Any]]: A list of structured festival dictionaries containing
                              name, fee, and deadlines.

    Raises:
        ValueError: If the JSON-LD script tag cannot be found or parsed.
    """
    # Search for the embedded JSON-LD script tag containing the ItemList schema[cite: 1]
    match = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', html_content)

    if not match:
        raise ValueError("JSON-LD script tag not found in the HTML response[cite: 1].")

    try:
        ld_json = json.loads(match[1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode JSON-LD payload: {e}")

    festivals = []

    # Verify the schema type and extract the items from the ItemList[cite: 1]
    if ld_json.get("@type") == "ItemList" and "itemListElement" in ld_json:
        for element in ld_json["itemListElement"]:
            event = element.get("item", {})

            # Map fields safely with fallback defaults
            festival_record = {
                "name": event.get("name", "Unknown Festival"),
                "fee": 0.0,  # Default numeric fee value
                "tier_deadline": event.get("startDate", "TBD"),
                "absolute_deadline": event.get("startDate", "TBD")
            }
            festivals.append(festival_record)

    return festivals