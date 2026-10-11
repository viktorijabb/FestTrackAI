import pytest
from pathlib import Path
from festtrackai.db.database import init_db, insert_festival, get_all_festivals

@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Creates a temporary SQLite database for isolated testing."""
    db_file = tmp_path / "test_festivals.db"
    init_db(db_file)
    return db_file

def test_insert_and_get_festival(temp_db: Path):
    """Test inserting a festival record and retrieving it from the database."""
    festival = {
        "name": "IndieLeeds Film Fest",
        "fee": 10.0,
        "deadline": "20/09/2026"
    }

    insert_festival(festival, db_path=temp_db)
    festivals = get_all_festivals(db_path=temp_db)

    assert len(festivals) == 1
    assert festivals[0]["name"] == "IndieLeeds Film Fest"
    assert festivals[0]["fee"] == 10.0
    assert festivals[0]["deadline"] == "20/09/2026"
    assert festivals[0]["status"] == "Unapplied"