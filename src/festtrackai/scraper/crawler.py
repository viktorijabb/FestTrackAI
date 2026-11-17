from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from festtrackai.models.festival import Festival
from pydantic import ValidationError

def parse_festival_html(html_content: str) -> Festival | None:
    """Parses raw HTML from a festival card and returns a validated Festival model."""
    soup = BeautifulSoup(html_content, "html.parser")

    title_el = soup.select_one(".festival-title, [data-test='festival-title'], h3, h2")
    fee_el = soup.select_one(".festival-fee, [data-test='festival-fee'], .fee")
    tier_deadline_el = soup.select_one(".tier-deadline, .deadline-tier")
    absolute_deadline_el = soup.select_one(".absolute-deadline, .deadline-absolute")

    if not title_el or not fee_el:
        return None

    fee_text = fee_el.text.replace("$", "").replace("£", "").strip()
    try:
        fee_val = float(fee_text)
    except ValueError:
        fee_val = 0.0

    try:
        return Festival(
            name=title_el.text.strip(),
            fee=fee_val,
            tier_deadline=tier_deadline_el.text.strip() if tier_deadline_el else "TBD",
            absolute_deadline=absolute_deadline_el.text.strip() if absolute_deadline_el else "TBD",
            status="Unapplied"
        )
    except ValidationError:
        return None

def fetch_filmfreeway_festivals() -> list[Festival]:
    """Launches a headless browser instance with custom headers to scrape FilmFreeway."""
    festivals = []
    target_url = "https://filmfreeway.com/festivals"

    with sync_playwright() as p:
        # Launch browser with a standard desktop user agent to avoid basic blocks
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Navigate and wait for network activity to settle
            page.goto(
                "https://filmfreeway.com/festivals",
                wait_until="domcontentloaded",
                timeout=30000
            )

            # Allow extra time for dynamic elements to mount
            page.wait_for_selector(".festival-card, [data-test='festival-card'], div", timeout=10000)

            cards = page.query_selector_all(".festival-card, [data-test='festival-card']")
            for card in cards:
                html = card.inner_html()
                validated_festival = parse_festival_html(html)
                if validated_festival:
                    festivals.append(validated_festival)
        except Exception as e:
            print(f"Scraping encountered an issue: {e}")
        finally:
            browser.close()

    return festivals