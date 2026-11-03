FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN python -m pip install --no-cache-dir . \
    && groupadd --system taskmanager \
    && useradd --system --gid taskmanager --home-dir /app --no-create-home taskmanager \
    && mkdir /data \
    && chown taskmanager:taskmanager /data

WORKDIR /data
USER taskmanager

CMD ["python", "-m", "task_manager.cli"]
