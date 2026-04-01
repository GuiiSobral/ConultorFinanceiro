import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
DB_PATH = DB_DIR / "family_budget.db"


ENTRY_COLUMNS = {
    "status": "TEXT DEFAULT 'confirmed'",
    "extraction_source": "TEXT DEFAULT 'manual_review'",
    "reviewed_at": "TEXT",
}


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def ensure_entry_columns(connection: sqlite3.Connection) -> None:
    for column_name, column_definition in ENTRY_COLUMNS.items():
        if not column_exists(connection, "entries", column_name):
            connection.execute(
                f"ALTER TABLE entries ADD COLUMN {column_name} {column_definition}"
            )


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                occurred_on TEXT,
                source_kind TEXT NOT NULL,
                raw_text TEXT,
                entry_type TEXT,
                amount REAL,
                currency TEXT DEFAULT 'BRL',
                category TEXT,
                subcategory TEXT,
                payment_method TEXT,
                description TEXT,
                confidence REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'confirmed',
                extraction_source TEXT DEFAULT 'manual_review',
                reviewed_at TEXT
            )
            """
        )
        ensure_entry_columns(conn)
        conn.commit()


def insert_entry(entry: dict) -> int:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO entries (
                submission_id,
                captured_at,
                occurred_on,
                source_kind,
                raw_text,
                entry_type,
                amount,
                currency,
                category,
                subcategory,
                payment_method,
                description,
                confidence,
                status,
                extraction_source,
                reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.get("submission_id"),
                entry.get("captured_at"),
                entry.get("occurred_on"),
                entry.get("source_kind", "text"),
                entry.get("raw_text"),
                entry.get("entry_type"),
                entry.get("amount"),
                entry.get("currency", "BRL"),
                entry.get("category"),
                entry.get("subcategory"),
                entry.get("payment_method"),
                entry.get("description"),
                entry.get("confidence", 0),
                entry.get("status", "confirmed"),
                entry.get("extraction_source", "manual_review"),
                entry.get("reviewed_at"),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def confirm_entry(entry: dict) -> int:
    payload = {
        "submission_id": entry.get("submission_id"),
        "captured_at": entry.get("captured_at"),
        "occurred_on": entry.get("occurred_on"),
        "source_kind": "text",
        "raw_text": entry.get("raw_text"),
        "entry_type": entry.get("entry_type"),
        "amount": entry.get("amount"),
        "currency": entry.get("currency", "BRL"),
        "category": entry.get("category"),
        "subcategory": entry.get("subcategory"),
        "payment_method": entry.get("payment_method"),
        "description": entry.get("description"),
        "confidence": entry.get("confidence", 0),
        "status": "confirmed",
        "extraction_source": "manual_review",
        "reviewed_at": entry.get("captured_at"),
    }
    return insert_entry(payload)


def update_entry(entry_id: int, entry: dict) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE entries
            SET occurred_on = ?,
                raw_text = ?,
                entry_type = ?,
                amount = ?,
                currency = ?,
                category = ?,
                subcategory = ?,
                payment_method = ?,
                description = ?,
                confidence = ?,
                extraction_source = 'manual_edit',
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                entry.get("occurred_on"),
                entry.get("raw_text"),
                entry.get("entry_type"),
                entry.get("amount"),
                entry.get("currency", "BRL"),
                entry.get("category"),
                entry.get("subcategory"),
                entry.get("payment_method"),
                entry.get("description"),
                entry.get("confidence", 0),
                entry_id,
            ),
        )
        conn.commit()


def cancel_entry(entry_id: int) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE entries
            SET status = 'cancelled',
                extraction_source = 'manual_edit',
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (entry_id,),
        )
        conn.commit()


def list_entries(
    start_date: str | None = None,
    end_date: str | None = None,
    entry_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[dict]:
    init_db()
    conditions = []
    params: list[object] = []

    if start_date:
        conditions.append("date(occurred_on) >= date(?)")
        params.append(start_date)
    if end_date:
        conditions.append("date(occurred_on) <= date(?)")
        params.append(end_date)
    if entry_type:
        conditions.append("entry_type = ?")
        params.append(entry_type)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if status and status != "all":
        conditions.append("status = ?")
        params.append(status)
    elif not status:
        conditions.append("status != 'cancelled'")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT
            id,
            submission_id,
            captured_at,
            occurred_on,
            source_kind,
            raw_text,
            entry_type,
            amount,
            currency,
            category,
            subcategory,
            payment_method,
            description,
            confidence,
            status,
            extraction_source,
            reviewed_at,
            created_at
        FROM entries
        {where_clause}
        ORDER BY date(COALESCE(occurred_on, captured_at)) DESC, id DESC
        LIMIT ?
    """
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]
