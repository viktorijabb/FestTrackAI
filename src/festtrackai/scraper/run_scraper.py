from festtrackai.scraper.crawler import fetch_filmfreeway_festivals
from festtrackai.db.database import init_db, insert_festival

def run():
    """Initializes the database and scrapes festival listings from FilmFreeway."""
    init_db()

    print("🚀 Launching scraper targeting FilmFreeway...")

    try:
        scraped_festivals = fetch_filmfreeway_festivals()

        if not scraped_festivals:
            print("⚠️ No valid festivals found or page structure did not match selectors.")
            return

        for festival in scraped_festivals:
            insert_festival(festival.model_dump())

        print(f"✅ Successfully saved {len(scraped_festivals)} festivals from FilmFreeway!")

    except Exception as e:
        print(f"❌ An error occurred during scraping: {e}")

if __name__ == "__main__":
    run()