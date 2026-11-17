"""Run with PYTHONPATH=src python -m unittest discover -s tests -p 'test_ingestion_regressions.py'."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from pydantic import ValidationError
from festtrackai.main import app
from festtrackai.utils import is_valid_fee
from festtrackai.scraper.parser import parse_filmfreeway_html
from festtrackai.models.festival import Festival
from festtrackai.db.database import init_db, insert_festival, get_all_festivals, update_festival_status


def html(value, tag='<script type="application/ld+json">'):
    return tag + json.dumps(value) + '</script>'


def listing(*events):
    return {"@type": "ItemList", "itemListElement": [{"item": e} for e in events]}


class ParserTests(unittest.TestCase):
    def test_live_listing_fixture(self):
        body = (Path(__file__).parent / "fixtures/filmfreeway-listing.html").read_text()
        records = parse_filmfreeway_html(body)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["name"], "Toronto Short Film Festival")
        self.assertIsNone(records[0]["fee"])
        self.assertEqual(records[0]["absolute_deadline"], "TBD")

    def test_attribute_variations_and_later_script(self):
        body = html({"@type": "Organization"}) + html(listing({"name": "A & B"}),
            "<SCRIPT id='festivals' TYPE = 'application/ld+json; charset=utf-8'>")
        self.assertEqual(parse_filmfreeway_html(body)[0]["name"], "A & B")

    def test_graph_array_and_references(self):
        data = [{"@graph": [{"@type": ["Thing", "https://schema.org/ItemList"],
                 "itemListElement": [{"item": {"@id": "#festival"}}]},
                 {"@id": "#festival", "name": "Referenced"}]}]
        self.assertEqual(parse_filmfreeway_html(html(data))[0]["name"], "Referenced")

    def test_direct_items_and_multiple_lists(self):
        data = [listing({"name": "First"}), {"@type": "ItemList",
                "itemListElement": [{"@type": "Event", "name": "Second"}]}]
        self.assertEqual(len(parse_filmfreeway_html(html(data))), 2)

    def test_does_not_invent_submission_metadata(self):
        record = parse_filmfreeway_html(html(listing({"name": "A", "startDate": "2027-01-01",
                      "offers": {"price": 15, "priceCurrency": "USD"}})))[0]
        self.assertIsNone(record["fee"])
        self.assertEqual(record["tier_deadline"], "TBD")
        self.assertEqual(record["absolute_deadline"], "TBD")

    def test_explicit_fields_retained(self):
        record = {"name": "A", "fee": 0, "tier_deadline": "2027-01-01", "absolute_deadline": "2027-02-01"}
        self.assertEqual(parse_filmfreeway_html(html(listing(record))), [record])

    def test_empty_list_is_valid(self):
        self.assertEqual(parse_filmfreeway_html(html(listing())), [])

    def test_invalid_payloads(self):
        for body in ['', '{{ $json.data }}', '<html>Challenge</html>', '{"data":"html"}',
                     html({"@type": "Organization"}),
                     '<script type="application/ld+json">{broken}</script>',
                     html({"@type": "ItemList", "itemListElement": {}}),
                     html({"@type": "ItemList", "itemListElement": ["#missing"]})]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_filmfreeway_html(body)

    def test_malformed_script_does_not_silently_drop_records(self):
        with self.assertRaises(ValueError):
            parse_filmfreeway_html(html(listing({"name": "A"})) +
                '<script type="application/ld+json">{broken}</script>')

    def test_unknown_fee_does_not_pass_budget_filter(self):
        self.assertFalse(is_valid_fee(None))
        self.assertTrue(is_valid_fee(0))

    def test_model_rejects_invalid_values(self):
        for value in [-1, float('nan'), float('inf')]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Festival(name="A", fee=value)
        with self.assertRaises(ValidationError):
            Festival(name="  ")


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "festivals.db"

    def tearDown(self):
        self.temp.cleanup()

    def test_legacy_migration_preserves_data_and_ids(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE festivals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, fee REAL NOT NULL, tier_deadline TEXT NOT NULL, absolute_deadline TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Unapplied')")
            conn.execute("INSERT INTO festivals VALUES (42, 'Legacy', 0, 'old', 'old', 'Submitted')")
        init_db(self.db)
        init_db(self.db)
        self.assertEqual(get_all_festivals(self.db)[0], dict(id=42, name="Legacy", fee=0,
                         tier_deadline="old", absolute_deadline="old", status="Submitted"))
        self.assertEqual(insert_festival(dict(name="Unknown", fee=None, tier_deadline="TBD",
                         absolute_deadline="TBD"), self.db), "inserted")

    def test_refresh_preserves_status_and_known_fields(self):
        init_db(self.db)
        record = dict(name="A", fee=12, tier_deadline="2027-01-01", absolute_deadline="2027-02-01")
        self.assertEqual(insert_festival(record, self.db), "inserted")
        update_festival_status(1, "Submitted", self.db)
        self.assertEqual(insert_festival({**record, "fee": 0}, self.db), "updated")
        insert_festival({**record, "fee": None, "tier_deadline": "TBD"}, self.db)
        rows = get_all_festivals(self.db)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fee"], 0)
        self.assertEqual(rows[0]["status"], "Submitted")
        self.assertEqual(rows[0]["tier_deadline"], "2027-01-01")


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.temp.name)
        self.context = TestClient(app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        os.chdir(self.cwd)
        self.temp.cleanup()

    def post(self, *records):
        return self.client.post('/api/v1/festivals/ingest-html', content=html(listing(*records)),
                                headers={"Content-Type": "text/html"})

    def test_fresh_database_and_repeat_counts(self):
        self.assertTrue(Path('festivals.db').exists())
        first = self.post({"name": "A"}).json()
        second = self.post({"name": "A", "fee": "$10"}).json()
        self.assertEqual(first["inserted_records"], 1)
        self.assertEqual(second["inserted_records"], 0)
        self.assertEqual(second["updated_records"], 1)
        self.assertEqual(get_all_festivals()[0]["fee"], 10)

    def test_unknown_fee_is_not_free(self):
        self.assertEqual(self.post({"name": "A"}).status_code, 200)
        self.assertIsNone(get_all_festivals()[0]["fee"])

    def test_partial_validation_and_all_failed(self):
        response = self.post({"name": "A"}, {"name": ""})
        self.assertEqual(response.json()["status"], "partial_success")
        self.assertEqual(response.json()["failed_records"], 1)
        self.assertEqual(self.post({"name": ""}).status_code, 422)
        self.assertEqual(self.post({"name": "B", "fee": "£12"}).status_code, 422)

    def test_parse_failure_and_invalid_encoding(self):
        for body in [b'{{ $json.data }}', b'<html>Challenge</html>', b'\xff']:
            self.assertEqual(self.client.post('/api/v1/festivals/ingest-html', content=body).status_code, 400)

    def test_storage_failure_is_not_success(self):
        with self.assertLogs('festtrackai.api.routes', level='ERROR'), patch('festtrackai.api.routes.insert_festival', side_effect=sqlite3.OperationalError('disk full')):
            self.assertEqual(self.post({"name": "A"}).status_code, 500)

    def test_more_than_ten_festivals_in_one_page(self):
        response = self.post(*[{"name": f"Festival {i}"} for i in range(12)])
        self.assertEqual(response.json()["inserted_records"], 12)


if __name__ == '__main__':
    unittest.main()
