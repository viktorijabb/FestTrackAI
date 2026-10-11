from festtrackai.scraper.crawler import parse_festival_html

def test_parse_festival_html_valid_data():
    """Test that raw HTML content correctly parses into structured festival records."""
    sample_html = """
    <div class="festival-card">
        <h2 class="festival-title">IndieLeeds Film Fest</h2>
        <span class="festival-fee">$10.00</span>
        <span class="festival-deadline">20/09/2026</span>
    </div>
    """

    festival = parse_festival_html(sample_html)

    assert festival is not None
    assert festival.name == "IndieLeeds Film Fest"
    assert festival.fee == 10.0
    assert festival.deadline == "20/09/2026"