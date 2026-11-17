# tests/integration/test_database.py
from pathlib import Path
from festtrackai.db.database import insert_festival, get_all_festivals, init_db

def test_insert_and_get_festival(tmp_path: Path):
    db_path = tmp_path / "test_festivals.db"
    init_db(db_path=db_path)

    festival = {
        "name": "IndieLeeds Film Fest",
        "fee": 10.0,
        "tier_deadline": "2026-09-20T00:00:00",
        "absolute_deadline": "2026-09-25T00:00:00"
    }

    insert_festival(festival, db_path=db_path)
    festivals = get_all_festivals(db_path=db_path)

    assert len(festivals) == 1
    assert festivals[0]["name"] == "IndieLeeds Film Fest"
