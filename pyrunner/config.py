from __future__ import annotations

import os


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.sandbox_image: str = os.getenv("SANDBOX_IMAGE", "python:3.12-slim")
        self.pool_size: int = int(os.getenv("POOL_SIZE", "2"))
        self.exec_timeout: int = int(os.getenv("EXEC_TIMEOUT", "30"))
        self.max_output_size: int = int(os.getenv("MAX_OUTPUT_SIZE", "50000"))
        self.mcp_host: str = os.getenv("MCP_HOST", "0.0.0.0")
        self.mcp_port: int = int(os.getenv("MCP_PORT", "8000"))
        self.container_memory_limit: str = os.getenv("CONTAINER_MEMORY_LIMIT", "256m")
        self.container_cpu_limit: float = float(os.getenv("CONTAINER_CPU_LIMIT", "1.0"))


settings = Settings()
