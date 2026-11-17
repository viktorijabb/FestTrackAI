import pytest
from datetime import datetime
from festtrackai.utils import is_valid_fee, parse_deadline

def test_is_valid_fee():
    """Test that only festivals with a fee of $10 or less are accepted."""
    # Valid fees based on project constraints and sample data
    assert is_valid_fee(9.42) is True   # Positively Different Short Film[cite: 1]
    assert is_valid_fee(3.0) is True    # Batman Film Fest[cite: 1]
    assert is_valid_fee(10.0) is True   # IndieLeeds[cite: 1]

    # Invalid fees exceeding the $10 threshold
    assert is_valid_fee(14.0) is False  # Short Movie Club[cite: 1]
    assert is_valid_fee(11.0) is False  # London Night[cite: 1]

def test_parse_deadline():
    """Test that deadline string formats parse into correct datetime objects."""
    date_str = "20/09/2026"
    parsed_date = parse_deadline(date_str)

    assert isinstance(parsed_date, datetime)
    assert parsed_date.year == 2026
    assert parsed_date.month == 9
    assert parsed_date.day == 20