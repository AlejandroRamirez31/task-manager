"""SQLite connection and schema setup."""

import sqlite3
from pathlib import Path


def connect_database(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite database and configure rows for named-column access."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the tasks table if needed without committing the caller's transaction."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL CHECK (
                length(trim(title, char(9) || char(10) || char(11) || char(12) || char(13) || ' ')) > 0
            ),
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'in_progress', 'completed')),
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )