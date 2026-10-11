from festtrackai.db.database import init_db, insert_festival
from pathlib import Path

def seed_database():
    """Initializes the database and inserts sample festival records with dual deadlines."""
    db_path = Path("festivals.db")
    if db_path.exists():
        db_path.unlink()  # Clean slate for schema update

    init_db()

    sample_festivals = [
        {
            "name": "Positively Different Short Film Festival",
            "fee": 9.42,
            "tier_deadline": "01/03/2026",
            "absolute_deadline": "15/03/2026",
            "status": "Unapplied"
        },
        {
            "name": "Batman Film Fest",
            "fee": 3.00,
            "tier_deadline": "10/04/2026",
            "absolute_deadline": "22/04/2026",
            "status": "Unapplied"
        },
        {
            "name": "IndieLeeds Film Fest",
            "fee": 10.00,
            "tier_deadline": "01/09/2026",
            "absolute_deadline": "20/09/2026",
            "status": "Unapplied"
        },
        {
            "name": "Short Movie Club",
            "fee": 14.00,
            "tier_deadline": "25/04/2026",
            "absolute_deadline": "10/05/2026",
            "status": "Unapplied"
        },
        {
            "name": "London Night Film Festival",
            "fee": 11.00,
            "tier_deadline": "15/06/2026",
            "absolute_deadline": "30/06/2026",
            "status": "Unapplied"
        }
    ]

    for festival in sample_festivals:
        insert_festival(festival)

    print("Database successfully re-seeded with dual-deadline festival records!")

if __name__ == "__main__":
    seed_database()