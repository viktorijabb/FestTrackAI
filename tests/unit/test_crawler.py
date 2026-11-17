# tests/unit/test_crawler.py
from festtrackai.scraper.parser import parse_filmfreeway_html

def test_parse_filmfreeway_html_valid_data():
    """Test that raw HTML content correctly parses into structured festival records."""
    sample_html = """
    <script type="application/ld+json">
    {
        "@type": "ItemList",
        "itemListElement": [
            {
                "item": {
                    "name": "IndieLeeds Film Fest",
                    "url": "https://filmfreeway.com/indieleeds"
                }
            }
        ]
    }
    </script>
    """

    festivals = parse_filmfreeway_html(sample_html)

    assert len(festivals) > 0
    assert festivals[0]["name"] == "IndieLeeds Film Fest"
    # assert festival.fee == 10.0
    # assert festival.tier_deadline == "20/09/2026"
    # assert festival.absolute_deadline is not None