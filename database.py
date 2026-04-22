import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY,
                repo TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                issue_type TEXT,
                assigned_agent TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(repo, issue_number)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                issue_id INTEGER REFERENCES issues(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_issue(repo: str, issue_number: int) -> int:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO issues (repo, issue_number) VALUES (?, ?)",
            (repo, issue_number),
        )
        row = conn.execute(
            "SELECT id FROM issues WHERE repo = ? AND issue_number = ?",
            (repo, issue_number),
        ).fetchone()
        return row["id"]


def update_issue(issue_id: int, issue_type: str, assigned_agent: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE issues SET issue_type = ?, assigned_agent = ? WHERE id = ?",
            (issue_type, assigned_agent, issue_id),
        )


def get_issue(repo: str, issue_number: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM issues WHERE repo = ? AND issue_number = ?",
            (repo, issue_number),
        ).fetchone()
        return dict(row) if row else None


def add_message(issue_id: int, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (issue_id, role, content) VALUES (?, ?, ?)",
            (issue_id, role, content),
        )


def get_messages(issue_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE issue_id = ? ORDER BY created_at",
            (issue_id,),
        ).fetchall()
        return [dict(r) for r in rows]
