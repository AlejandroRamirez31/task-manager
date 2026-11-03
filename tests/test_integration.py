from pathlib import Path
import sqlite3

import pytest

from task_manager import cli
from task_manager.database import connect_database
from task_manager.repository import TaskRepository
from task_manager.service import TaskService


def _run_cli(
    monkeypatch: pytest.MonkeyPatch,
    database_path: Path,
    responses: list[str],
) -> None:
    response_iterator = iter(responses)
    monkeypatch.setattr(cli, "DATABASE_PATH", database_path)
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": next(response_iterator),
    )
    cli.main()


def test_cli_completes_task_crud_flow_with_real_sqlite(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "lifecycle.db"
    _run_cli(
        monkeypatch,
        database_path,
        [
            "1",
            "  Plan release  ",
            "  Include rollout notes  ",
            "in_progress",
            "2",
            "3",
            "1",
            "4",
            "1",
            "Ship release",
            "",
            "yes",
            "",
            "3",
            "1",
            "5",
            "1",
            "yes",
            "6",
        ],
    )

    output = capsys.readouterr().out
    assert "Task created." in output
    assert "Title: Plan release" in output
    assert "Description:   Include rollout notes  " in output
    assert "Status: in_progress" in output
    assert "Title: Ship release" in output
    assert "Title: Ship release\nStatus: in_progress\nDescription: \n" in output
    assert "Task updated." in output
    assert "Task 1 deleted." in output

    connection = connect_database(database_path)
    try:
        row = connection.execute(
            "SELECT COUNT(*) AS task_count FROM tasks"
        ).fetchone()
        assert row["task_count"] == 0
    finally:
        connection.close()


def test_task_persists_after_cli_closes_and_database_reopens(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "persistent.db"
    opened_connections: list[sqlite3.Connection] = []
    real_connect_database = cli.connect_database

    def capture_connection(path: Path) -> sqlite3.Connection:
        connection = real_connect_database(path)
        opened_connections.append(connection)
        return connection

    monkeypatch.setattr(cli, "connect_database", capture_connection)
    _run_cli(
        monkeypatch,
        database_path,
        ["1", "  Persist this task  ", "  Keep these spaces  ", "completed", "6"],
    )

    assert len(opened_connections) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        opened_connections[0].execute("SELECT 1")

    connection = connect_database(database_path)
    try:
        service = TaskService(TaskRepository(connection))
        task = service.get_task(1)

        assert task.id == 1
        assert task.title == "Persist this task"
        assert task.description == "  Keep these spaces  "
        assert task.status == "completed"
        assert task.created_at is not None
        assert task.updated_at is not None
    finally:
        connection.close()
