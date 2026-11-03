"""Data models used by the task manager."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Task:
    """A task and its persisted metadata."""

    title: str
    description: str = ""
    status: str = "pending"
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None