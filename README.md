# Task Manager

Task Manager is a command-line application for managing tasks in a local SQLite database.

## Architecture

- **Model (`models.py`):** Represents tasks and their status and timestamp fields.
- **Database (`database.py`):** Opens SQLite connections configured for named-column rows and initializes the schema.
- **Repository (`repository.py`):** Performs parameterized SQLite CRUD operations and maps rows to task objects.
- **Service (`service.py`):** Validates and normalizes task input, delegates persistence, and reports missing tasks.
- **CLI (`cli.py`):** Provides the interactive menu, displays results and errors, and owns connection and transaction management.

## Features

- Create, list, view, update, and delete tasks.
- Track task status as `pending`, `in_progress`, or `completed`.
- Validate task titles, descriptions, statuses, and IDs.
- Update selected task fields or clear a description.
- Store UTC timestamps in SQLite and expose them as timezone-aware Python datetimes.
- Confirm deletions and preserve changes through SQLite transactions.

## Requirements

- Python 3.10 or later.
- No third-party runtime dependencies. The package uses Python's built-in `sqlite3` module.
- The project uses `setuptools` (version 61 or later) as its build backend. `pip` installs the build requirement when installing the project.
- `pytest` (version 8 or later) is an optional development dependency used for tests.

## Install

From the project directory, install the package in editable mode with its test dependency:

```text
python -m pip install -e ".[dev]"
```

The `dev` extra installs pytest. To install only the application, use `python -m pip install -e .` instead.

## Run

From the project directory, start the interactive application with:

```text
python -m task_manager.cli
```

The CLI creates or opens `tasks.db` in the process's current working directory. If you launch the application from another directory, the database file is created or opened there instead.

## Tests

Run the complete test suite with:

```text
python -m pytest
```