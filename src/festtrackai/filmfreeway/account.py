"""Local-only browser sessions. Never transmit these files to scraping services."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit
from uuid import uuid4

from festtrackai.filmfreeway.html import Document

BASE = 'https://filmfreeway.com'


class SessionRequired(ValueError):
    pass


def session_path():
    return Path(os.environ.get('FESTTRACKAI_FILMFREEWAY_SESSION',
                               '.filmfreeway/session.json'))


def signed_in(html):
    # Observed on FilmFreeway pages: an explicit boolean, not a Gold badge,
    # marketing copy, or merely the presence of a cookie.
    root = Document(html).root
    for script in root.all('script'):
        if script.attrs.get('type') == 'early-loader-globals':
            try:
                return json.loads(script.text()).get('user_signed_in') is True
            except (ValueError, AttributeError):
                return False
    return False


def load_session():
    try:
        value = json.loads(session_path().read_text())
        if (value.get('version') != 1 or value.get('membership') not in ('standard', 'gold')
                or value.get('membership_source') != 'user-confirmed'
                or not isinstance(value.get('storage_state'), dict)
                or not isinstance(value.get('generation'), str)):
            raise ValueError()
        return value
    except (OSError, ValueError, AttributeError):
        raise SessionRequired('Connect FilmFreeway using the local login helper first.') from None


def save_session(state, membership):
    if membership not in ('standard', 'gold'):
        raise ValueError('Choose standard or gold membership.')
    # A Google sign-in may have populated other origins: keep FilmFreeway only.
    state = {
        'cookies': [c for c in state.get('cookies', [])
                    if c.get('domain', '').lstrip('.') in ('filmfreeway.com', 'www.filmfreeway.com')],
        'origins': [o for o in state.get('origins', [])
                    if o.get('origin') in (BASE, 'https://www.filmfreeway.com')],
    }
    value = dict(version=1, generation=uuid4().hex, membership=membership,
                 membership_source='user-confirmed',
                 connected_at=datetime.now(timezone.utc).isoformat(), storage_state=state)
    path = session_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return value


def disconnect():
    session_path().unlink(missing_ok=True)


def festival_url(value):
    parsed = urlsplit(value.strip())
    if (parsed.scheme != 'https' or parsed.hostname not in ('filmfreeway.com', 'www.filmfreeway.com')
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError('Use an https://filmfreeway.com festival profile URL.')
    slug = parsed.path.strip('/')
    if (not slug or '/' in slug or not all(c.isascii() and (c.isalnum() or c in '-_') for c in slug)
            or slug.lower() in {'login', 'logout', 'sign_up', 'festivals', 'projects', 'submissions', 'cart'}):
        raise ValueError('Paste a festival profile URL, not a listing or account page.')
    return BASE + '/' + slug


def login(membership='standard', timeout=300):
    """Open a visible browser on the user's desktop and wait for manual sign-in."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(BASE + '/login', wait_until='domcontentloaded')
            print('Sign in directly on FilmFreeway in the opened browser. This window closes after verification.')
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                if page.is_closed():
                    raise SessionRequired('Login cancelled. No new session was saved.')
                if urlsplit(page.url).hostname in ('filmfreeway.com', 'www.filmfreeway.com'):
                    if signed_in(page.content()):
                        check = context.new_page()
                        check.goto(BASE + '/festivals', wait_until='domcontentloaded')
                        if signed_in(check.content()):
                            save_session(context.storage_state(), membership)
                            print('FilmFreeway session saved locally. Membership is user-confirmed: ' + membership)
                            return
                        check.close()
                page.wait_for_timeout(1000)
            raise SessionRequired('Login timed out. No new session was saved.')
        finally:
            browser.close()


def fetch_prices(url):
    from playwright.sync_api import sync_playwright
    from festtrackai.filmfreeway.pricing import parse_prices
    url = festival_url(url)
    session = load_session()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(storage_state=session['storage_state'])
            # Cookies stay domain-scoped in the local browser, never in a hosted scraper.
            page = context.new_page()
            response = page.goto(url, wait_until='domcontentloaded', timeout=45000)
            if response is None or response.status >= 400:
                raise ValueError('FilmFreeway could not load the festival. Try again later.')
            if urlsplit(page.url).hostname not in ('filmfreeway.com', 'www.filmfreeway.com'):
                raise SessionRequired('FilmFreeway redirected away from the festival. Reconnect your account.')
            html = page.content()
            if not signed_in(html):
                raise SessionRequired('FilmFreeway session expired or could not be verified. Reconnect before loading account prices.')
            rows = parse_prices(html, session['membership'])
            if not rows:
                raise ValueError('No current category fee table found. The event may be closed or its layout may have changed.')
            # Do not return a disconnected or replaced account's in-flight result.
            if load_session()['generation'] != session['generation']:
                raise SessionRequired('Account changed while loading. Refresh prices again.')
            return dict(url=url, membership=session['membership'],
                        membership_source=session['membership_source'], generation=session['generation'],
                        checked_at=datetime.now(timezone.utc).isoformat(), prices=rows)
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description='Connect your local FestTrackAI installation to FilmFreeway')
    parser.add_argument('action', choices=['login', 'disconnect'])
    parser.add_argument('--membership', choices=['standard', 'gold'], default='standard',
                        help='Your current membership, confirmed by you; never inferred from a festival badge')
    args = parser.parse_args()
    if args.action == 'disconnect':
        disconnect()
        print('Local FilmFreeway session removed.')
    else:
        try:
            login(args.membership)
        except Exception:
            # Browser exceptions can contain URLs/session material; do not dump them.
            parser.exit(1, 'Could not connect. Run on your desktop, install Playwright Chromium, and complete login within five minutes.\n')


if __name__ == '__main__':
    main()
