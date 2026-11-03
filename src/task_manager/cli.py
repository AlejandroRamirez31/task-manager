"""Interactive command-line interface for the task manager."""

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from task_manager.database import connect_database, initialize_database
from task_manager.models import Task
from task_manager.repository import TaskRepository
from task_manager.service import TaskNotFoundError, TaskService

DATABASE_PATH = Path("tasks.db")
_Result = TypeVar("_Result")


def main() -> None:
    """Initialize the application, run its menu, and close its connection."""
    connection: sqlite3.Connection | None = None
    try:
        connection = connect_database(DATABASE_PATH)
        initialize_database(connection)
        connection.commit()
        service = TaskService(TaskRepository(connection))
        _run_menu(service, connection)
    except (EOFError, KeyboardInterrupt):
        print("\nExiting Task Manager.")
    except sqlite3.Error as error:
        print(f"Database error: {error}")
    finally:
        if connection is not None:
            connection.close()


def _run_menu(service: TaskService, connection: sqlite3.Connection) -> None:
    while True:
        print("\nTask Manager")
        print("1. Create task")
        print("2. List tasks")
        print("3. View task")
        print("4. Update task")
        print("5. Delete task")
        print("6. Exit")
        choice = input("Choose an option (1-6): ").strip()

        if choice == "6":
            print("Goodbye.")
            return

        try:
            if choice == "1":
                _create_task(service, connection)
            elif choice == "2":
                _list_tasks(service)
            elif choice == "3":
                _view_task(service)
            elif choice == "4":
                _update_task(service, connection)
            elif choice == "5":
                _delete_task(service, connection)
            else:
                print("Invalid menu choice. Select a number from 1 to 6.")
        except ValueError as error:
            print(f"Input error: {error}")
        except TaskNotFoundError as error:
            print(f"Task not found: {error}")
        except sqlite3.Error as error:
            print(f"Database error: {error}")


def _create_task(service: TaskService, connection: sqlite3.Connection) -> None:
    title = input("Title: ")
    description = input("Description: ")
    status = input("Status [pending]: ").strip()

    if status:
        operation = lambda: service.create_task(title, description, status)
    else:
        operation = lambda: service.create_task(title, description)
    task = _run_write(connection, operation)
    print("Task created.")
    _print_task(task)


def _list_tasks(service: TaskService) -> None:
    tasks = service.list_tasks()
    if not tasks:
        print("No tasks found.")
        return
    for task in tasks:
        _print_task(task)


def _view_task(service: TaskService) -> None:
    task = service.get_task(_read_task_id())
    _print_task(task)


def _update_task(service: TaskService, connection: sqlite3.Connection) -> None:
    task_id = _read_task_id()
    current_task = service.get_task(task_id)
    print("Current task:")
    _print_task(current_task)

    title_input = input("New title (blank keeps current): ")
    status_input = input("New status (blank keeps current): ").strip()
    description_choice = input("Change description? [y/N]: ").strip().lower()

    if description_choice in {"y", "yes"}:
        description = input("New description (empty clears it): ")
    elif description_choice in {"", "n", "no"}:
        description = None
    else:
        print("Please answer yes or no. No changes made.")
        return

    title = title_input if title_input else None
    status = status_input if status_input else None
    if title is None and status is None and description is None:
        print("No changes requested.")
        return

    updated_task = _run_write(
        connection,
        lambda: service.update_task(
            task_id,
            title=title,
            description=description,
            status=status,
        ),
    )
    print("Task updated.")
    _print_task(updated_task)


def _delete_task(service: TaskService, connection: sqlite3.Connection) -> None:
    task_id = _read_task_id()
    confirmation = input(f"Delete task {task_id}? [y/N]: ").strip().lower()
    if confirmation not in {"y", "yes"}:
        print("Deletion cancelled.")
        return

    _run_write(connection, lambda: service.delete_task(task_id))
    print(f"Task {task_id} deleted.")


def _read_task_id() -> int:
    raw_task_id = input("Task ID: ").strip()
    try:
        return int(raw_task_id)
    except ValueError:
        raise ValueError("Please enter a whole-number task ID.") from None


def _print_task(task: Task) -> None:
    print(f"ID: {task.id}")
    print(f"Title: {task.title}")
    print(f"Status: {task.status}")
    print(f"Description: {task.description}")


def _run_write(
    connection: sqlite3.Connection,
    operation: Callable[[], _Result],
) -> _Result:
    try:
        result = operation()
        connection.commit()
        return result
    except BaseException:
        connection.rollback()
        raise


if __name__ == "__main__":
    main()