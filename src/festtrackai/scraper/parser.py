"""Deterministic extraction from intact FilmFreeway JSON-LD metadata."""
import json
from html.parser import HTMLParser


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self.parts = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            mime = dict(attrs).get("type") or ""
            if mime.split(";")[0].strip().lower() == "application/ld+json":
                self.parts = []

    def handle_data(self, data):
        if self.parts is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.parts is not None:
            self.scripts.append("".join(self.parts))
            self.parts = None


def _nodes(value):
    if isinstance(value, list):
        for item in value:
            yield from _nodes(item)
    elif isinstance(value, dict):
        yield value
        for item in value.values():
            if isinstance(item, (dict, list)):
                yield from _nodes(item)


def _has_type(node, expected):
    types = node.get("@type", [])
    if isinstance(types, str):
        types = [types]
    return isinstance(types, list) and any(
        isinstance(t, str) and t.rstrip("/").rsplit("/", 1)[-1] == expected
        for t in types
    )


def parse_filmfreeway_html(html_content: str) -> list[dict]:
    if not html_content.strip():
        raise ValueError("Empty HTML body; forward the scraper's original HTML response.")
    if "{{" in html_content and "$json" in html_content:
        raise ValueError("Unevaluated n8n expression; use expression mode for the Send body.")
    parser = _Scripts()
    parser.feed(html_content)
    if not parser.scripts:
        raise ValueError(
            "No JSON-LD script found. Send intact HTML (not clean_text or JSON); "
            "check the scraper output for a login or challenge page."
        )
    documents = []
    invalid = 0
    for script in parser.scripts:
        try:
            documents.append(json.loads(script.lstrip("\ufeff")))
        except json.JSONDecodeError:
            invalid += 1
    nodes = list(_nodes(documents))
    # Only definitions, rather than bare references, belong in the index.
    by_id = {n["@id"]: n for n in nodes
             if isinstance(n.get("@id"), str) and len(n) > 1}
    def resolve(node):
        if isinstance(node, str):
            return by_id.get(node)
        if isinstance(node, dict) and set(node) == {"@id"}:
            return by_id.get(node["@id"]) if isinstance(node["@id"], str) else None
        return node
    lists = [n for n in nodes if _has_type(n, "ItemList")]
    if not lists:
        raise ValueError(
            "No festival ItemList found in JSON-LD. Verify the scraped page is the festival listing."
            + (f" {invalid} malformed JSON-LD script(s)." if invalid else "")
        )
    festivals = []
    for listing in lists:
        elements = listing.get("itemListElement")
        if not isinstance(elements, list):
            raise ValueError("ItemList.itemListElement must be an array.")
        for element in elements:
            element = resolve(element)
            if not isinstance(element, dict):
                raise ValueError("Unresolved or invalid ItemList entry.")
            event = resolve(element.get("item", element))
            if not isinstance(event, dict):
                raise ValueError("Unresolved or invalid festival item.")
            # A directory's Event.startDate is NOT a submission deadline, and
            # offers.price can be an admission ticket. Only explicit submission
            # fields are mapped; missing facts remain unknown.
            festivals.append({
                "name": event.get("name", ""),
                "fee": event.get("fee"),
                "tier_deadline": event.get("tier_deadline") or "TBD",
                "absolute_deadline": event.get("absolute_deadline") or "TBD",
            })
    # Do not silently accept incomplete data if another script was malformed.
    if invalid:
        raise ValueError(f"{invalid} malformed JSON-LD script(s); cannot guarantee complete extraction.")
    return festivals
