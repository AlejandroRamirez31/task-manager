from datetime import timezone
import sqlite3
from typing import Iterator

import pytest

from task_manager.database import connect_database, initialize_database
from task_manager.models import Task
from task_manager.repository import TaskRepository


@pytest.fixture
def database_connection(tmp_path) -> Iterator[sqlite3.Connection]:
    connection = connect_database(tmp_path / "tasks.db")
    initialize_database(connection)
    connection.commit()
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def repository(database_connection: sqlite3.Connection) -> TaskRepository:
    return TaskRepository(database_connection)


def test_repository_rejects_connection_without_sqlite_row_factory(tmp_path) -> None:
    connection = sqlite3.connect(tmp_path / "unconfigured.db")
    try:
        with pytest.raises(ValueError, match="requires sqlite3.Row"):
            TaskRepository(connection)
    finally:
        connection.close()


def test_create_returns_task_with_database_metadata(repository: TaskRepository) -> None:
    task = repository.create("Review 'quoted'; DROP TABLE tasks; --")

    assert isinstance(task, Task)
    assert task.id is not None
    assert task.title == "Review 'quoted'; DROP TABLE tasks; --"
    assert task.description == ""
    assert task.status == "pending"
    assert task.created_at is not None
    assert task.created_at.tzinfo == timezone.utc
    assert task.updated_at is not None
    assert task.updated_at.tzinfo == timezone.utc
    assert len(repository.list_all()) == 1


def test_create_uses_provided_task_values(repository: TaskRepository) -> None:
    task = repository.create("Write tests", "Cover repository behavior", "in_progress")

    assert task.title == "Write tests"
    assert task.description == "Cover repository behavior"
    assert task.status == "in_progress"


def test_create_does_not_commit_or_close_caller_connection(
    database_connection: sqlite3.Connection,
) -> None:
    repository = TaskRepository(database_connection)

    task = repository.create("Temporary task")

    assert database_connection.in_transaction
    assert database_connection.execute("SELECT 1").fetchone()[0] == 1
    database_connection.rollback()
    assert repository.get_by_id(task.id) is None


def test_list_all_returns_empty_list_and_orders_by_id(repository: TaskRepository) -> None:
    assert repository.list_all() == []

    first = repository.create("First")
    second = repository.create("Second")

    assert repository.list_all() == [first, second]


def test_get_by_id_returns_task_or_none(repository: TaskRepository) -> None:
    created = repository.create("Find me")

    assert repository.get_by_id(created.id) == created
    assert repository.get_by_id(-1) is None


def test_update_changes_only_provided_fields_and_refreshes_timestamp(
    database_connection: sqlite3.Connection,
    repository: TaskRepository,
) -> None:
    created = repository.create("Keep this title", "Remove this description", "pending")
    stale_timestamp = "not-a-timestamp"
    database_connection.execute(
        "UPDATE tasks SET updated_at = ? WHERE id = ?",
        (stale_timestamp, created.id),
    )
    database_connection.commit()

    updated = repository.update(created.id, description="")

    assert updated is not None
    assert updated.id == created.id
    assert updated.title == "Keep this title"
    assert updated.description == ""
    assert updated.status == "pending"
    assert updated.created_at == created.created_at
    assert updated.updated_at is not None
    assert updated.updated_at.tzinfo == timezone.utc


def test_update_can_change_title_and_status(repository: TaskRepository) -> None:
    created = repository.create("Old title")

    updated = repository.update(created.id, title="New title", status="completed")

    assert updated is not None
    assert updated.title == "New title"
    assert updated.status == "completed"


def test_update_returns_none_for_missing_task(repository: TaskRepository) -> None:
    assert repository.update(-1, title="Missing") is None


def test_update_rejects_empty_change_set(repository: TaskRepository) -> None:
    with pytest.raises(ValueError, match="At least one task field"):
        repository.update(1)


def test_delete_reports_whether_task_existed(repository: TaskRepository) -> None:
    task = repository.create("Delete me")

    assert repository.delete(task.id)
    assert not repository.delete(task.id)
    assert repository.get_by_id(task.id) is None


def test_database_constraints_are_preserved(repository: TaskRepository) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        repository.create("Invalid status", status="blocked")


def test_invalid_stored_timestamp_is_not_silently_accepted(
    database_connection: sqlite3.Connection,
    repository: TaskRepository,
) -> None:
    task = repository.create("Corrupt timestamp")
    database_connection.execute(
        "UPDATE tasks SET created_at = ? WHERE id = ?",
        ("not-a-timestamp", task.id),
    )

    with pytest.raises(ValueError):
        repository.get_by_id(task.id)