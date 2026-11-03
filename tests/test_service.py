import sqlite3
from unittest.mock import Mock

import pytest

from task_manager.models import Task
from task_manager.repository import TaskRepository
from task_manager.service import TaskNotFoundError, TaskService


@pytest.fixture
def repository() -> Mock:
    return Mock(spec=TaskRepository)


@pytest.fixture
def service(repository: Mock) -> TaskService:
    return TaskService(repository)


@pytest.fixture
def sample_task() -> Task:
    return Task(title="Prepare report", id=1)


def test_create_task_normalizes_title_and_delegates_values(
    repository: Mock,
    service: TaskService,
    sample_task: Task,
) -> None:
    repository.create.return_value = sample_task

    result = service.create_task("  Prepare report  ", "Quarterly results", "pending")

    assert result is sample_task
    repository.create.assert_called_once_with(
        "Prepare report", "Quarterly results", "pending"
    )


def test_create_task_uses_default_description_and_status(
    repository: Mock,
    service: TaskService,
    sample_task: Task,
) -> None:
    repository.create.return_value = sample_task

    service.create_task("Prepare report")

    repository.create.assert_called_once_with("Prepare report", "", "pending")


def test_create_task_trims_title_edges_and_preserves_internal_whitespace(
    repository: Mock,
    service: TaskService,
    sample_task: Task,
) -> None:
    repository.create.return_value = sample_task

    service.create_task("  Learn Python programming  ")

    repository.create.assert_called_once_with(
        "Learn Python programming", "", "pending"
    )


def test_create_task_preserves_description_whitespace(
    repository: Mock,
    service: TaskService,
    sample_task: Task,
) -> None:
    repository.create.return_value = sample_task
    description = "  Important notes  "

    service.create_task("Prepare report", description)

    repository.create.assert_called_once_with("Prepare report", description, "pending")


@pytest.mark.parametrize("title", ["", "   ", "\t\n", "\u2003\u00a0"])
def test_create_task_rejects_empty_or_whitespace_title(
    repository: Mock,
    service: TaskService,
    title: str,
) -> None:
    with pytest.raises(ValueError, match="Title must not be empty"):
        service.create_task(title)

    repository.create.assert_not_called()


def test_create_task_rejects_non_string_title(
    repository: Mock,
    service: TaskService,
) -> None:
    with pytest.raises(ValueError, match="Title must be a string"):
        service.create_task(None)  # type: ignore[arg-type]

    repository.create.assert_not_called()


@pytest.mark.parametrize("status", ["pending", "in_progress", "completed"])
def test_create_task_accepts_supported_statuses(
    repository: Mock,
    service: TaskService,
    sample_task: Task,
    status: str,
) -> None:
    repository.create.return_value = sample_task

    service.create_task("Prepare report", status=status)

    repository.create.assert_called_once_with("Prepare report", "", status)


@pytest.mark.parametrize("status", ["blocked", "Pending", "", None])
def test_create_task_rejects_unsupported_status(
    repository: Mock,
    service: TaskService,
    status: str | None,
) -> None:
    with pytest.raises(ValueError, match="Status must be one of"):
        service.create_task("Prepare report", status=status)  # type: ignore[arg-type]

    repository.create.assert_not_called()


def test_create_task_rejects_non_string_description(
    repository: Mock,
    service: TaskService,
) -> None:
    with pytest.raises(ValueError, match="Description must be a string"):
        service.create_task("Prepare report", description=None)  # type: ignore[arg-type]

    repository.create.assert_not_called()


def test_list_tasks_returns_repository_result(
    repository: Mock,
    service: TaskService,
    sample_task: Task,
) -> None:
    repository.list_all.return_value = [sample_task]

    assert service.list_tasks() == [sample_task]
    repository.list_all.assert_called_once_with()


def test_list_tasks_returns_empty_list(repository: Mock, service: TaskService) -> None:
    repository.list_all.return_value = []

    assert service.list_tasks() == []


def test_get_task_returns_repository_result(
    repository: Mock,
    service: TaskService,
    sample_task: Task,
) -> None:
    repository.get_by_id.return_value = sample_task

    assert service.get_task(1) is sample_task
    repository.get_by_id.assert_called_once_with(1)


@pytest.mark.parametrize("task_id", [0, -1, True, 1.5, "1", None])
def test_get_task_rejects_invalid_id(
    repository: Mock,
    service: TaskService,
    task_id: object,
) -> None:
    with pytest.raises(ValueError, match="Task ID must be a positive integer"):
        service.get_task(task_id)  # type: ignore[arg-type]

    repository.get_by_id.assert_not_called()


def test_get_task_raises_for_missing_task(repository: Mock, service: TaskService) -> None:
    repository.get_by_id.return_value = None

    with pytest.raises(TaskNotFoundError, match="ID 42"):
        service.get_task(42)


def test_update_task_preserves_partial_update_behavior(
    repository: Mock,
    service: TaskService,
    sample_task: Task,
) -> None:
    repository.update.return_value = sample_task

    result = service.update_task(1, title="  New title ", description="")

    assert result is sample_task
    repository.update.assert_called_once_with(
        1,
        title="New title",
        description="",
        status=None,
    )


def test_update_task_rejects_empty_change_set(
    repository: Mock,
    service: TaskService,
) -> None:
    with pytest.raises(ValueError, match="At least one task field"):
        service.update_task(1)

    repository.update.assert_not_called()


@pytest.mark.parametrize(
    ("changes", "error_message"),
    [
        ({"title": "  "}, "Title must not be empty"),
        ({"description": 123}, "Description must be a string"),
        ({"status": "blocked"}, "Status must be one of"),
    ],
)
def test_update_task_rejects_invalid_supplied_fields(
    repository: Mock,
    service: TaskService,
    changes: dict[str, object],
    error_message: str,
) -> None:
    with pytest.raises(ValueError, match=error_message):
        service.update_task(1, **changes)  # type: ignore[arg-type]

    repository.update.assert_not_called()


def test_update_task_raises_for_missing_task(
    repository: Mock,
    service: TaskService,
) -> None:
    repository.update.return_value = None

    with pytest.raises(TaskNotFoundError, match="ID 42"):
        service.update_task(42, status="completed")


def test_delete_task_succeeds_when_repository_deletes_task(
    repository: Mock,
    service: TaskService,
) -> None:
    repository.delete.return_value = True

    assert service.delete_task(1) is None
    repository.delete.assert_called_once_with(1)


def test_delete_task_raises_for_missing_task(
    repository: Mock,
    service: TaskService,
) -> None:
    repository.delete.return_value = False

    with pytest.raises(TaskNotFoundError, match="ID 42"):
        service.delete_task(42)


def test_mutations_reject_invalid_ids_before_repository_calls(
    repository: Mock,
    service: TaskService,
) -> None:
    with pytest.raises(ValueError, match="Task ID must be a positive integer"):
        service.update_task(True, title="New title")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Task ID must be a positive integer"):
        service.delete_task(0)

    repository.update.assert_not_called()
    repository.delete.assert_not_called()


def test_repository_errors_are_not_caught(
    repository: Mock,
    service: TaskService,
) -> None:
    repository.create.side_effect = sqlite3.OperationalError("database is locked")

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        service.create_task("Prepare report")