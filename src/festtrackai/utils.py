from datetime import datetime

def is_valid_fee(fee: float) -> bool:
    """Returns True if the festival submission fee is $10 or less."""
    return fee <= 10.0

def parse_deadline(date_str: str) -> datetime:
    """Parses a date string in DD/MM/YYYY format into a datetime object."""
    return datetime.strptime(date_str, "%d/%m/%Y")