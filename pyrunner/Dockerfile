FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project metadata and lock file first for layer caching
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock

# Copy application source
COPY main.py /app/main.py
COPY config.py /app/config.py
COPY core /app/core
COPY tasks /app/tasks
COPY tools /app/tools

RUN apt-get update && apt-get install -y \
    build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    uv sync --frozen

EXPOSE 8000

# NOTE: Run with Docker socket mounted:
#   docker run -v /var/run/docker.sock:/var/run/docker.sock mcp-codemode
CMD ["uv", "run", "python", "main.py"]
