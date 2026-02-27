"""Client configuration — loaded from environment variables."""

from __future__ import annotations
import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All settings can be overridden via env vars (case-insensitive)."""

    # MCP server
    mcp_server_url: str = "http://localhost:8000/mcp/"
    mcp_server_no_code_execute_url: str = "http://localhost:8000/mcp-no-code-execute/"

    # LLM
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-5.2"
    max_tool_rounds: int = 10  # safety limit on agentic loops
    logfire_token: str = os.getenv("LOGFIRE_TOKEN", "")  # for optional logging to Logfire

    # Proxy tokens (injected into forwarded requests)
    microsoft_graph_token: str = ""
    github_token: str = ""

    # FastAPI
    host: str = "0.0.0.0"
    port: int = 8080

    redis_username: str = os.getenv("REDIS_USERNAME", "")
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    redis_db: int = int(os.getenv("REDIS_DB", 0))

    model_config = {"env_prefix": "CLIENT_", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
