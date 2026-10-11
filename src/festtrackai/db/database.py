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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS festivals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                fee REAL NOT NULL,
                tier_deadline TEXT NOT NULL,
                absolute_deadline TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Unapplied'
            )
        """)
        conn.commit()

def insert_festival(festival: dict, db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Inserts a festival record into the database securely using parameters."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO festivals (name, fee, tier_deadline, absolute_deadline, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                festival["name"],
                festival["fee"],
                festival["tier_deadline"],
                festival["absolute_deadline"],
                festival.get("status", "Unapplied")
            )
        )
        conn.commit()

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