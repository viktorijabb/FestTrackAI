import pytest
from pydantic import ValidationError
from festtrackai.models.festival import Festival

def test_valid_festival_model():
    """Test that a valid festival dictionary successfully creates a model instance."""
    data = {
        "name": "IndieLeeds Film Fest",
        "fee": 10.0,
        "deadline": "20/09/2026"
    }
    festival = Festival(**data)
    assert festival.name == "IndieLeeds Film Fest"
    assert festival.fee == 10.0
    assert festival.deadline == "20/09/2026"
    assert festival.status == "Unapplied"

def test_invalid_festival_missing_name():
    """Test that missing required fields like name raise a ValidationError."""
    data = {
        "fee": 5.0,
        "deadline": "20/09/2026"
    }
    with pytest.raises(ValidationError):
        Festival(**data)

def test_invalid_festival_negative_fee():
    """Test that negative fees fail validation."""
    data = {
        "name": "Bad Fee Fest",
        "fee": -2.0,
        "deadline": "20/09/2026"
    }
    with pytest.raises(ValidationError):
        Festival(**data)