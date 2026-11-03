from datetime import datetime, timedelta
import sqlite3

import pytest

from task_manager.database import connect_database, initialize_database


def test_initialize_database_creates_tasks_table(tmp_path) -> None:
    database_path = tmp_path / "tasks.db"
    connection = connect_database(database_path)
    try:
        initialize_database(connection)
        initialize_database(connection)
        connection.commit()

        columns = connection.execute("PRAGMA table_info(tasks)").fetchall()
        column_names = {column["name"] for column in columns}

        assert column_names == {
            "id",
            "title",
            "description",
            "status",
            "created_at",
            "updated_at",
        }
    finally:
        connection.close()


def test_initialize_database_leaves_transaction_ownership_to_caller(tmp_path) -> None:
    connection = connect_database(tmp_path / "tasks.db")
    try:
        connection.execute("BEGIN")

        initialize_database(connection)

        assert connection.in_transaction
        connection.rollback()
        tasks_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tasks'"
        ).fetchone()

        assert tasks_table is None
    finally:
        connection.close()


def test_tasks_table_applies_defaults_and_constraints(tmp_path) -> None:
    connection = connect_database(tmp_path / "tasks.db")
    try:
        initialize_database(connection)
        connection.execute("INSERT INTO tasks (title) VALUES (?)", ("Write tests",))
        connection.commit()

        row = connection.execute("SELECT * FROM tasks").fetchone()

        assert row["status"] == "pending"
        assert row["description"] == ""
        for column_name in ("created_at", "updated_at"):
            timestamp_text = row[column_name]
            assert isinstance(timestamp_text, str)
            assert timestamp_text.endswith("Z")
            timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
            assert timestamp.utcoffset() == timedelta(0)

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO tasks (title, status) VALUES (?, ?)",
                ("Invalid status", "blocked"),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO tasks (title) VALUES (?)", ("   ",))
    finally:
        connection.close()


@pytest.mark.parametrize(
    "title",
    ["\t", "\n", "\r", "\v", "\f", " \t\r\n\v\f "],
)
def test_tasks_table_rejects_common_ascii_whitespace_only_titles(tmp_path, title) -> None:
    connection = connect_database(tmp_path / "tasks.db")
    try:
        initialize_database(connection)

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
    finally:
        connection.close()