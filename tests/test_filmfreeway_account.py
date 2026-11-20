import os
from pathlib import Path
import stat
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from festtrackai.filmfreeway.account import (save_session, load_session, disconnect,
    signed_in, festival_url, fetch_prices, login, SessionRequired)
from festtrackai.filmfreeway.pricing import parse_prices, amount

FIXTURE = (Path(__file__).parent / 'fixtures/filmfreeway-fees.html').read_text()
SIGNED_IN = FIXTURE.replace('"user_signed_in":false', '"user_signed_in":true').replace('2026-12-29', '2099-12-29')
TODAY = date(2026, 11, 20)


class PricingTests(unittest.TestCase):
    def test_standard_and_gold_use_actual_current_fee(self):
        standard = parse_prices(FIXTURE, 'standard', TODAY)
        gold = parse_prices(FIXTURE, 'gold', TODAY)
        self.assertEqual(len(standard), 1)
        self.assertEqual(standard[0]['fee'], 65)
        self.assertEqual(gold[0]['fee'], 58.5)
        self.assertEqual(gold[0]['deadline'], '2026-12-29')
        self.assertIn('user-confirmed', gold[0]['price_basis'])

    def test_missing_gold_falls_back_to_standard(self):
        row = parse_prices(FIXTURE.replace('Gold Members: $58.50',
            'Gold Members: Not available'), 'gold', TODAY)[0]
        self.assertEqual(row['fee'], 65)
        self.assertEqual(row['price_basis'], 'Standard')

    def test_zero_is_a_real_gold_price(self):
        page = FIXTURE.replace('Gold Members: $58.50', 'Gold Members: $0')
        self.assertEqual(parse_prices(page, 'gold', TODAY)[0]['fee'], 0)

    def test_currency_not_guessed_from_dollar_symbol(self):
        for currency in ['CAD', 'GBP', '']:
            with self.subTest(currency=currency):
                row = parse_prices(FIXTURE.replace('USD', currency), 'gold', TODAY)[0]
                self.assertIsNone(row['fee'])
                self.assertIn('$58.50', row['published_gold'])

    def test_stale_current_tier_excluded(self):
        self.assertEqual(parse_prices(FIXTURE, 'gold', date(2027, 1, 1)), [])

    def test_malformed_or_missing_prices_never_become_free(self):
        for text in ['N/A', '$10-$20', '£10', 'EUR 10', '', '-1']:
            self.assertIsNone(amount(text))
        self.assertEqual(amount('Gold Members: Free'), 0)
        self.assertEqual(amount('Standard: $1,250.50'), 1250.5)

    def test_duplicate_mobile_desktop_categories_are_not_repeated(self):
        self.assertEqual(len(parse_prices(FIXTURE + FIXTURE, 'gold', TODAY)), 1)

    def test_membership_choice_cannot_be_arbitrary(self):
        with self.assertRaises(ValueError):
            parse_prices(FIXTURE, 'premium', TODAY)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / '.filmfreeway/session.json'
        self.env = patch.dict(os.environ, {'FESTTRACKAI_FILMFREEWAY_SESSION': str(self.path)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def save(self, membership='gold'):
        return save_session({'cookies': [
            {'domain': '.filmfreeway.com', 'name': 'session', 'value': 'synthetic'},
            {'domain': '.google.com', 'name': 'other', 'value': 'discard'}],
            'origins': [{'origin': 'https://filmfreeway.com', 'localStorage': []},
                        {'origin': 'https://accounts.google.com', 'localStorage': []}]}, membership)

    def test_private_state_excludes_identity_provider_tokens(self):
        self.save()
        value = load_session()
        self.assertEqual(len(value['storage_state']['cookies']), 1)
        self.assertEqual(len(value['storage_state']['origins']), 1)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(value['membership_source'], 'user-confirmed')

    def test_disconnect_and_account_switch(self):
        first = self.save()['generation']
        second = self.save('standard')['generation']
        self.assertNotEqual(first, second)
        disconnect()
        self.assertFalse(self.path.exists())
        with self.assertRaises(SessionRequired):
            load_session()
        disconnect()

    def test_missing_and_corrupt_state(self):
        with self.assertRaises(SessionRequired):
            load_session()
        self.path.parent.mkdir()
        self.path.write_text('broken')
        with self.assertRaises(SessionRequired):
            load_session()

    def test_real_signin_marker_required(self):
        self.assertFalse(signed_in(FIXTURE))
        self.assertTrue(signed_in(SIGNED_IN))
        self.assertFalse(signed_in('<img alt="Gold Member">Logged in'))
        self.assertFalse(signed_in('<script type="early-loader-globals">{"user_signed_in":"true"}</script>'))

    def test_only_filmfreeway_profile_urls_accepted(self):
        self.assertEqual(festival_url('https://filmfreeway.com/TorontoShortFilmFestival?tracking=1'),
                         'https://filmfreeway.com/TorontoShortFilmFestival')
        for url in ['http://filmfreeway.com/Fest', 'https://evil.com/Fest',
                    'https://filmfreeway.com.evil.com/Fest', 'https://localhost/Fest',
                    'https://filmfreeway.com/login', 'https://filmfreeway.com/festivals',
                    'https://filmfreeway.com:123/Fest', 'https://user@filmfreeway.com/Fest',
                    'https://filmfreeway.com/%2e%2e', 'https://filmfreeway.com/account/settings']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                festival_url(url)

    def mock_browser(self, factory, content=SIGNED_IN):
        browser = factory.return_value.__enter__.return_value.chromium.launch.return_value
        context = browser.new_context.return_value
        page = context.new_page.return_value
        page.url = 'https://filmfreeway.com/TorontoShortFilmFestival'
        page.goto.return_value.status = 200
        page.content.return_value = content
        return browser, context, page

    @patch('playwright.sync_api.sync_playwright')
    def test_authenticated_fetch_uses_local_session(self, factory):
        self.save()
        browser, _, _ = self.mock_browser(factory)
        result = fetch_prices('https://filmfreeway.com/TorontoShortFilmFestival')
        self.assertEqual(result['prices'][0]['fee'], 58.5)
        self.assertNotIn('storage_state', result)
        self.assertEqual(browser.new_context.call_args.kwargs['storage_state']['cookies'][0]['value'], 'synthetic')
        browser.close.assert_called_once()

    @patch('playwright.sync_api.sync_playwright')
    def test_expired_session_stops_without_anonymous_fallback(self, factory):
        self.save()
        browser, _, _ = self.mock_browser(factory, FIXTURE)
        with self.assertRaises(SessionRequired):
            fetch_prices('https://filmfreeway.com/TorontoShortFilmFestival')
        browser.close.assert_called_once()

    @patch('playwright.sync_api.sync_playwright')
    def test_disconnect_during_fetch_invalidates_result(self, factory):
        self.save()
        _, _, page = self.mock_browser(factory)
        def content():
            disconnect()
            return SIGNED_IN
        page.content.side_effect = content
        with self.assertRaises(SessionRequired):
            fetch_prices('https://filmfreeway.com/TorontoShortFilmFestival')

    @patch('playwright.sync_api.sync_playwright')
    def test_login_saves_only_after_fresh_signin_verification(self, factory):
        browser, context, page = self.mock_browser(factory)
        page.is_closed.return_value = False
        context.storage_state.return_value = {'cookies': [], 'origins': []}
        login('gold', timeout=5)
        self.assertEqual(load_session()['membership'], 'gold')
        browser.close.assert_called_once()

    @patch('playwright.sync_api.sync_playwright')
    def test_cancelled_login_does_not_replace_existing_session(self, factory):
        original = self.save()['generation']
        browser, _, page = self.mock_browser(factory)
        page.is_closed.return_value = True
        with self.assertRaises(SessionRequired):
            login('standard', timeout=5)
        self.assertEqual(load_session()['generation'], original)
        browser.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
