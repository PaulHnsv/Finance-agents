FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git curl build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /workspace
COPY pyproject.toml .
RUN uv sync --no-install-project 2>/dev/null || true

ENV PYTHONPATH=/workspace/src
