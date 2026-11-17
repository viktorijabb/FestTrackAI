# tests/unit/test_models.py
from festtrackai.models.festival import Festival

def test_valid_festival_model():
    """Test that a valid festival dictionary successfully creates a model instance."""
    data = {
        "name": "IndieLeeds Film Fest",
        "fee": 10.0,
        "tier_deadline": "2026-09-20T00:00:00",
        "absolute_deadline": "2026-09-25T00:00:00"
    }
    festival = Festival(**data)
    assert festival.name == "IndieLeeds Film Fest"
    assert festival.tier_deadline is not None
    assert festival.absolute_deadline is not None