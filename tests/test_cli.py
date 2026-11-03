import sqlite3
from unittest.mock import Mock

import pytest

from task_manager import cli
from task_manager.models import Task
from task_manager.service import TaskNotFoundError, TaskService


@pytest.fixture
def service() -> Mock:
    return Mock(spec=TaskService)


@pytest.fixture
def connection() -> Mock:
    connection = Mock(spec=sqlite3.Connection)
    connection.row_factory = sqlite3.Row
    return connection


@pytest.fixture
def sample_task() -> Task:
    return Task(title="Prepare report", description="Quarterly results", id=1)


def _set_input(monkeypatch: pytest.MonkeyPatch, responses: list[str]) -> None:
    response_iter = iter(responses)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(response_iter))


def test_menu_repeats_and_exits(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["invalid", "6"])

    cli._run_menu(service, connection)

    output = capsys.readouterr().out
    assert "Invalid menu choice" in output
    assert "Goodbye." in output
    service.list_tasks.assert_not_called()


def test_create_task_uses_service_and_commits(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(monkeypatch, ["1", "  Prepare report  ", "  Keep spaces  ", "", "6"])
    service.create_task.return_value = sample_task

    cli._run_menu(service, connection)

    service.create_task.assert_called_once_with("  Prepare report  ", "  Keep spaces  ")
    connection.commit.assert_called_once_with()
    connection.rollback.assert_not_called()
    assert "Task created." in capsys.readouterr().out


def test_create_task_passes_explicit_status(
    monkeypatch: pytest.MonkeyPatch,
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(monkeypatch, ["1", "Prepare report", "Description", "completed", "6"])
    service.create_task.return_value = sample_task

    cli._run_menu(service, connection)

    service.create_task.assert_called_once_with("Prepare report", "Description", "completed")


def test_create_validation_error_rolls_back_and_menu_continues(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["1", "", "Description", "", "6"])
    service.create_task.side_effect = ValueError("Title must not be empty")

    cli._run_menu(service, connection)

    connection.rollback.assert_called_once_with()
    connection.commit.assert_not_called()
    assert "Input error: Title must not be empty" in capsys.readouterr().out


def test_list_tasks_displays_empty_result_without_committing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["2", "6"])
    service.list_tasks.return_value = []

    cli._run_menu(service, connection)

    service.list_tasks.assert_called_once_with()
    connection.commit.assert_not_called()
    assert "No tasks found." in capsys.readouterr().out


def test_list_tasks_displays_each_task(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(monkeypatch, ["2", "6"])
    service.list_tasks.return_value = [sample_task]

    cli._run_menu(service, connection)

    output = capsys.readouterr().out
    assert "ID: 1" in output
    assert "Title: Prepare report" in output
    assert "Status: pending" in output
    assert "Description: Quarterly results" in output


def test_view_task_parses_id_and_does_not_commit(
    monkeypatch: pytest.MonkeyPatch,
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(monkeypatch, ["3", "1", "6"])
    service.get_task.return_value = sample_task

    cli._run_menu(service, connection)

    service.get_task.assert_called_once_with(1)
    connection.commit.assert_not_called()


def test_malformed_task_id_shows_clear_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["3", "one", "6"])

    cli._run_menu(service, connection)

    service.get_task.assert_not_called()
    assert "Please enter a whole-number task ID." in capsys.readouterr().out


def test_update_task_preserves_description_whitespace_and_commits(
    monkeypatch: pytest.MonkeyPatch,
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(
        monkeypatch,
        ["4", "1", "", "", "yes", "  Important notes  ", "6"],
    )
    service.get_task.return_value = sample_task
    service.update_task.return_value = sample_task

    cli._run_menu(service, connection)

    service.update_task.assert_called_once_with(
        1,
        title=None,
        description="  Important notes  ",
        status=None,
    )
    connection.commit.assert_called_once_with()


def test_update_task_can_clear_description(
    monkeypatch: pytest.MonkeyPatch,
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(monkeypatch, ["4", "1", "", "", "y", "", "6"])
    service.get_task.return_value = sample_task
    service.update_task.return_value = sample_task

    cli._run_menu(service, connection)

    service.update_task.assert_called_once_with(
        1,
        title=None,
        description="",
        status=None,
    )
    connection.commit.assert_called_once_with()


def test_update_task_with_no_changes_does_not_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(monkeypatch, ["4", "1", "", "", "no", "6"])
    service.get_task.return_value = sample_task

    cli._run_menu(service, connection)

    service.update_task.assert_not_called()
    connection.commit.assert_not_called()
    assert "No changes requested." in capsys.readouterr().out


def test_update_invalid_description_choice_does_not_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(monkeypatch, ["4", "1", "", "", "maybe", "6"])
    service.get_task.return_value = sample_task

    cli._run_menu(service, connection)

    service.update_task.assert_not_called()
    connection.commit.assert_not_called()
    assert "Please answer yes or no." in capsys.readouterr().out


def test_update_validation_error_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
    sample_task: Task,
) -> None:
    _set_input(monkeypatch, ["4", "1", "", "blocked", "n", "6"])
    service.get_task.return_value = sample_task
    service.update_task.side_effect = ValueError("Status must be valid")

    cli._run_menu(service, connection)

    connection.rollback.assert_called_once_with()
    connection.commit.assert_not_called()
    assert "Input error: Status must be valid" in capsys.readouterr().out


def test_delete_confirmation_commits_only_after_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["5", "1", "yes", "6"])

    cli._run_menu(service, connection)

    service.delete_task.assert_called_once_with(1)
    connection.commit.assert_called_once_with()
    assert "Task 1 deleted." in capsys.readouterr().out


def test_cancelled_delete_does_not_commit_or_call_service(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["5", "1", "no", "6"])

    cli._run_menu(service, connection)

    service.delete_task.assert_not_called()
    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()
    assert "Deletion cancelled." in capsys.readouterr().out


def test_task_not_found_is_reported_and_menu_continues(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["3", "42", "6"])
    service.get_task.side_effect = TaskNotFoundError("Task with ID 42 was not found")

    cli._run_menu(service, connection)

    assert "Task not found: Task with ID 42 was not found" in capsys.readouterr().out


def test_database_error_is_reported_and_menu_continues(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["2", "6"])
    service.list_tasks.side_effect = sqlite3.OperationalError("database is locked")

    cli._run_menu(service, connection)

    assert "Database error: database is locked" in capsys.readouterr().out


def test_unexpected_programming_error_is_not_hidden(
    monkeypatch: pytest.MonkeyPatch,
    service: Mock,
    connection: Mock,
) -> None:
    _set_input(monkeypatch, ["2"])
    service.list_tasks.side_effect = RuntimeError("unexpected failure")

    with pytest.raises(RuntimeError, match="unexpected failure"):
        cli._run_menu(service, connection)


def test_main_initializes_dependencies_in_order_and_closes_connection(
    monkeypatch: pytest.MonkeyPatch,
    connection: Mock,
) -> None:
    order: list[str] = []
    repository = Mock()
    service = Mock()
    connection.commit.side_effect = lambda: order.append("commit")

    def connect(path: object) -> Mock:
        order.append("connect")
        assert path == cli.DATABASE_PATH
        return connection

    def initialize(received_connection: Mock) -> None:
        order.append("initialize")
        assert received_connection is connection

    def make_repository(received_connection: Mock) -> Mock:
        order.append("repository")
        assert received_connection is connection
        return repository

    def make_service(received_repository: Mock) -> Mock:
        order.append("service")
        assert received_repository is repository
        return service

    def run_menu(received_service: Mock, received_connection: Mock) -> None:
        order.append("menu")
        assert received_service is service
        assert received_connection is connection

    monkeypatch.setattr(cli, "connect_database", connect)
    monkeypatch.setattr(cli, "initialize_database", initialize)
    monkeypatch.setattr(cli, "TaskRepository", make_repository)
    monkeypatch.setattr(cli, "TaskService", make_service)
    monkeypatch.setattr(cli, "_run_menu", run_menu)

    cli.main()

    assert order == [
        "connect",
        "initialize",
        "commit",
        "repository",
        "service",
        "menu",
    ]
    connection.commit.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_main_closes_connection_when_initialization_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    connection: Mock,
) -> None:
    monkeypatch.setattr(cli, "connect_database", lambda _path: connection)
    monkeypatch.setattr(
        cli,
        "initialize_database",
        Mock(side_effect=sqlite3.OperationalError("cannot initialize")),
    )

    cli.main()

    connection.close.assert_called_once_with()
    connection.commit.assert_not_called()
    assert "Database error: cannot initialize" in capsys.readouterr().out


@pytest.mark.parametrize("interrupt", [EOFError, KeyboardInterrupt])
def test_main_handles_eof_and_interrupt_and_closes_connection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    connection: Mock,
    interrupt: type[BaseException],
) -> None:
    monkeypatch.setattr(cli, "connect_database", lambda _path: connection)
    monkeypatch.setattr(cli, "initialize_database", Mock())
    monkeypatch.setattr("builtins.input", Mock(side_effect=interrupt()))

    cli.main()

    connection.close.assert_called_once_with()
    assert "Exiting Task Manager." in capsys.readouterr().out


def test_write_helper_rolls_back_when_commit_fails(connection: Mock) -> None:
    connection.commit.side_effect = sqlite3.OperationalError("commit failed")

    with pytest.raises(sqlite3.OperationalError, match="commit failed"):
        cli._run_write(connection, lambda: "written")

    connection.rollback.assert_called_once_with()