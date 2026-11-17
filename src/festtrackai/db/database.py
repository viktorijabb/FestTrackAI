import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("festivals.db")

def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Creates and returns a database connection with row factory configured."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Initializes the SQLite database schema with separate tier and absolute deadlines."""
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS festivals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                fee REAL,
                tier_deadline TEXT NOT NULL,
                absolute_deadline TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Unapplied'
            )
        """)
        # SQLite cannot drop NOT NULL in place. Preserve IDs, status and data
        # when upgrading the original schema to allow unknown fees.
        columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(festivals)")}
        if columns["fee"]["notnull"]:
            conn.execute("ALTER TABLE festivals RENAME TO festivals_legacy")
            conn.execute("""
                CREATE TABLE festivals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    fee REAL,
                    tier_deadline TEXT NOT NULL,
                    absolute_deadline TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Unapplied'
                )
            """)
            conn.execute("""INSERT INTO festivals (id, name, fee, tier_deadline, absolute_deadline, status)
                            SELECT id, name, fee, tier_deadline, absolute_deadline, status
                            FROM festivals_legacy""")
            conn.execute("DROP TABLE festivals_legacy")
        conn.commit()

def insert_festival(festival: dict, db_path: Path | str = DEFAULT_DB_PATH) -> str:
    """Refresh known metadata while preserving submission status and unknown fields."""
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT id FROM festivals WHERE name = ?",
                                (festival["name"],)).fetchone()
        conn.execute(
            """
            INSERT INTO festivals (name, fee, tier_deadline, absolute_deadline, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                fee = COALESCE(excluded.fee, festivals.fee),
                tier_deadline = CASE WHEN excluded.tier_deadline = 'TBD'
                    THEN festivals.tier_deadline ELSE excluded.tier_deadline END,
                absolute_deadline = CASE WHEN excluded.absolute_deadline = 'TBD'
                    THEN festivals.absolute_deadline ELSE excluded.absolute_deadline END
            """,
            (festival["name"], festival.get("fee"), festival["tier_deadline"],
             festival["absolute_deadline"], festival.get("status", "Unapplied")),
        )
        conn.commit()
    return "updated" if existing else "inserted"

def get_all_festivals(db_path: Path | str = DEFAULT_DB_PATH) -> list[dict]:
    """Retrieves all festival records from the database as dictionaries."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM festivals")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def update_festival_status(festival_id: int, status: str, db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Updates the application status of a specific festival by its ID."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE festivals 
            SET status = ? 
            WHERE id = ?
            """,
            (status, festival_id)
        )
        conn.commit()
