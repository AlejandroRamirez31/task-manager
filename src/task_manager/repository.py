"""SQLite persistence operations for tasks."""

import sqlite3
from datetime import datetime, timezone

from task_manager.models import Task


class TaskRepository:
    """Read and write tasks using a caller-owned SQLite connection.

    The connection must use ``sqlite3.Row`` for named-column access. Create it
    with ``connect_database()`` from the database module.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        if connection.row_factory is not sqlite3.Row:
            raise ValueError(
                "TaskRepository requires sqlite3.Row; use connect_database()"
            )
        self._connection = connection

    def create(
        self,
        title: str,
        description: str = "",
        status: str = "pending",
    ) -> Task:
        """Insert a task and return it with its database-assigned metadata."""
        cursor = self._connection.execute(
            """
            INSERT INTO tasks (title, description, status)
            VALUES (?, ?, ?)
            """,
            (title, description, status),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an ID for the new task")

        task = self.get_by_id(cursor.lastrowid)
        if task is None:
            raise RuntimeError("The newly created task could not be retrieved")
        return task

    def list_all(self) -> list[Task]:
        """Return all tasks in ascending ID order."""
        rows = self._connection.execute(
            "SELECT * FROM tasks ORDER BY id ASC"
        ).fetchall()
        return [_row_to_task(row) for row in rows]

    def get_by_id(self, task_id: int) -> Task | None:
        """Return one task, or None when its ID does not exist."""
        row = self._connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_task(row)

    def update(
        self,
        task_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> Task | None:
        """Update supplied fields and return the task, or None if it is missing."""
        updates = {
            column: value
            for column, value in (
                ("title", title),
                ("description", description),
                ("status", status),
            )
            if value is not None
        }
        if not updates:
            raise ValueError("At least one task field must be provided")

        assignments = [f"{column} = ?" for column in updates]
        assignments.append("updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')")
        parameters = (*updates.values(), task_id)
        cursor = self._connection.execute(
            f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?",
            parameters,
        )
        if cursor.rowcount == 0:
            return None
        return self.get_by_id(task_id)

    def delete(self, task_id: int) -> bool:
        """Delete a task and report whether a row was removed."""
        cursor = self._connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )
        return cursor.rowcount > 0


def _row_to_task(row: sqlite3.Row) -> Task:
    """Convert a SQLite row to a task with timezone-aware UTC timestamps."""
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        created_at=_parse_utc_timestamp(row["created_at"]),
        updated_at=_parse_utc_timestamp(row["updated_at"]),
    )


def _parse_utc_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp and normalize it to timezone-aware UTC."""
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError(f"Stored timestamp is not timezone-aware: {value!r}")
    return timestamp.astimezone(timezone.utc)