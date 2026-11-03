from datetime import datetime
from typing import get_type_hints

from task_manager.models import Task


def test_task_has_expected_defaults() -> None:
    task = Task(title="Prepare report")

    assert task.title == "Prepare report"
    assert task.description == ""
    assert task.status == "pending"
    assert task.id is None
    assert task.created_at is None
    assert task.updated_at is None


def test_task_timestamp_fields_are_datetime_or_none() -> None:
    field_types = get_type_hints(Task)

    assert field_types["created_at"] == datetime | None
    assert field_types["updated_at"] == datetime | None