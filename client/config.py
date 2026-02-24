"""Client configuration — loaded from environment variables."""

from __future__ import annotations
import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All settings can be overridden via env vars (case-insensitive)."""

    # MCP server
    mcp_server_url: str = "http://localhost:8000/mcp"

    # LLM
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-5.2"
    max_tool_rounds: int = 10  # safety limit on agentic loops

    # FastAPI
    host: str = "0.0.0.0"
    port: int = 8080

    model_config = {"env_prefix": "CLIENT_", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
