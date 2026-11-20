"""Read explicit Standard/Gold category prices; never apply a guessed discount."""
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re
from festtrackai.filmfreeway.html import Document


def amount(text):
    # Do not confuse an unrecognised currency, range or missing price with free.
    text = text.split(':', 1)[-1].strip()
    if text.lower() == 'free':
        return 0.0
    match = re.fullmatch(r'(?:US\$|\$|USD\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)', text)
    if not match:
        return None
    try:
        return float(Decimal(match[1].replace(',', '')))
    except InvalidOperation:
        return None


def _currencies(root):
    def walk(value):
        if isinstance(value, dict):
            if 'priceCurrency' in value:
                yield value['priceCurrency']
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
    result = set()
    for script in root.all('script'):
        if script.attrs.get('type') == 'application/ld+json':
            try:
                result.update(v for v in walk(json.loads(script.text())) if isinstance(v, str))
            except ValueError:
                continue
    return result


def parse_prices(html, membership='standard', today=None):
    if membership not in ('standard', 'gold'):
        raise ValueError('Unknown membership choice.')
    today = today or date.today()
    root = Document(html).root
    currencies = _currencies(root)
    # A dollar symbol alone is ambiguous: verify USD in the page metadata.
    currency = next(iter(currencies)) if len(currencies) == 1 else None
    dates = {}
    for group in root.all(cls='ProfileFestival-datesDeadlines-dateGroup'):
        label = next(group.all(cls='ProfileFestival-datesDeadlines-deadline'), None)
        time = next(group.all('time'), None)
        if label and time:
            try:
                dates[label.text()] = date.fromisoformat(time.attrs.get('datetime', '')[:10])
            except ValueError:
                continue
    result = []
    seen = set()
    for category in root.all(attr='data-category-item'):
        name = next(category.all(cls='festival-category-name'), None)
        if not name:
            continue
        tier = None
        standard = gold = None
        raw_standard = raw_gold = None

        def finish():
            if tier is None:
                return
            deadline = dates.get(tier)
            if deadline and deadline < today:
                return
            key = (name.text(), tier)
            if key in seen:
                return
            seen.add(key)
            use_gold = membership == 'gold' and gold is not None
            chosen = gold if use_gold else standard
            numeric = chosen if currency == 'USD' else None
            result.append(dict(category=name.text(), tier=tier,
                deadline=deadline.isoformat() if deadline else None,
                standard_fee=standard if currency == 'USD' else None,
                gold_fee=gold if currency == 'USD' else None,
                fee=numeric, currency=currency or 'Unknown',
                price_basis='Gold (user-confirmed membership)' if use_gold else 'Standard',
                published_standard=raw_standard, published_gold=raw_gold))

        for item in category.all('li'):
            classes = item.attrs.get('class', '').split()
            if 'CategoryName' in classes:
                finish()
                tier = item.text() if 'is-current' in classes else None
                standard = gold = None
                raw_standard = raw_gold = None
            elif tier and 'Fee' in classes:
                if 'GoldFee' in classes:
                    raw_gold = item.text()
                    gold = amount(raw_gold)
                else:
                    raw_standard = item.text()
                    standard = amount(raw_standard)
        finish()
    return result
