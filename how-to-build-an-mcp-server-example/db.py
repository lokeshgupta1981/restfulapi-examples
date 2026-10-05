"""SQLite storage for the task tracker example.

Run `python db.py` to create (or reset) tasks.db with the sample data.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("tasks.db")

SCHEMA = """
CREATE TABLE projects (
    key   TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    owner TEXT NOT NULL
);
CREATE TABLE tasks (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    project  TEXT NOT NULL REFERENCES projects(key),
    title    TEXT NOT NULL,
    status   TEXT NOT NULL CHECK (status IN ('todo', 'in_progress', 'done')),
    assignee TEXT,
    due_date TEXT
);
"""

PROJECTS = [
    ("APP", "Mobile app 2.0", "maria"),
    ("WEB", "Website redesign", "dev"),
]

TASKS = [
    ("APP", "Add login with passkeys", "in_progress", "maria", "2026-10-15"),
    ("APP", "Fix crash on Android 15 startup", "todo", "omar", "2026-10-09"),
    ("APP", "Write release notes", "todo", None, "2026-10-20"),
    ("APP", "Set up crash reporting", "done", "omar", "2026-09-30"),
    ("WEB", "New pricing page", "in_progress", "dev", "2026-10-12"),
    ("WEB", "Migrate blog to static site", "todo", "dev", None),
]


def connect() -> sqlite3.Connection:
    """Open the database and return rows as dict-like objects."""
    if not DB_PATH.exists():
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create a fresh database with the sample projects and tasks."""
    DB_PATH.unlink(missing_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO projects VALUES (?, ?, ?)", PROJECTS)
    conn.executemany(
        "INSERT INTO tasks (project, title, status, assignee, due_date) VALUES (?, ?, ?, ?, ?)",
        TASKS,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Created {DB_PATH.name} with {len(PROJECTS)} projects and {len(TASKS)} tasks")
