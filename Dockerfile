FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY main.py /app/main.py
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock

RUN apt-get update && apt-get install -y \
    build-essential && \
    uv sync --frozen

CMD [ "uv", "run", "main.py" ]
