"""Business rules for task operations."""

from task_manager.models import Task
from task_manager.repository import TaskRepository

_VALID_STATUSES = frozenset({"pending", "in_progress", "completed"})


class TaskNotFoundError(LookupError):
    """Raised when an operation refers to a task that does not exist."""


class TaskService:
    """Validate task operations and delegate persistence to a repository."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "pending",
    ) -> Task:
        """Validate and create a task."""
        normalized_title = _normalize_title(title)
        _validate_description(description)
        _validate_status(status)
        return self._repository.create(normalized_title, description, status)

    def list_tasks(self) -> list[Task]:
        """Return all tasks from the repository."""
        return self._repository.list_all()

    def get_task(self, task_id: int) -> Task:
        """Return a task by ID, raising TaskNotFoundError if it is absent."""
        _validate_task_id(task_id)
        task = self._repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task with ID {task_id} was not found")
        return task

    def update_task(
        self,
        task_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> Task:
        """Validate and update only the supplied task fields."""
        _validate_task_id(task_id)
        if title is None and description is None and status is None:
            raise ValueError("At least one task field must be provided")

        normalized_title = None if title is None else _normalize_title(title)
        if description is not None:
            _validate_description(description)
        if status is not None:
            _validate_status(status)

        task = self._repository.update(
            task_id,
            title=normalized_title,
            description=description,
            status=status,
        )
        if task is None:
            raise TaskNotFoundError(f"Task with ID {task_id} was not found")
        return task

    def delete_task(self, task_id: int) -> None:
        """Delete a task, raising TaskNotFoundError if it does not exist."""
        _validate_task_id(task_id)
        if not self._repository.delete(task_id):
            raise TaskNotFoundError(f"Task with ID {task_id} was not found")


def _normalize_title(title: str) -> str:
    if not isinstance(title, str):
        raise ValueError("Title must be a string")
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("Title must not be empty or whitespace-only")
    return normalized_title


def _validate_description(description: str) -> None:
    if not isinstance(description, str):
        raise ValueError("Description must be a string")


def _validate_status(status: str) -> None:
    if not isinstance(status, str) or status not in _VALID_STATUSES:
        allowed_statuses = ", ".join(sorted(_VALID_STATUSES))
        raise ValueError(f"Status must be one of: {allowed_statuses}")


def _validate_task_id(task_id: int) -> None:
    if isinstance(task_id, bool) or not isinstance(task_id, int) or task_id <= 0:
        raise ValueError("Task ID must be a positive integer")