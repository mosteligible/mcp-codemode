import os


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.code_execution_host: str = os.getenv(
            "CODE_EXECUTION_HOST", "https://localhost:8080"
        )
        self.max_output_size: int = int(os.getenv("MAX_OUTPUT_SIZE", "50000"))
        self.mcp_host: str = os.getenv("MCP_HOST", "0.0.0.0")
        self.mcp_port: int = int(os.getenv("MCP_PORT", "8000"))
        self.container_memory_limit: str = os.getenv("CONTAINER_MEMORY_LIMIT", "256m")
        self.container_cpu_limit: float = float(os.getenv("CONTAINER_CPU_LIMIT", "1.0"))

        self.supervisor_agent_model: str = os.getenv(
            "SUPERVISOR_AGENT_MODEL", "openai:gpt-5.4"
        )
        self.default_static_agent_model: str = os.getenv(
            "DEFAULT_STATIC_AGENT_MODEL", "openai:gpt-5.2"
        )
        self.github_agent_model: str = os.getenv(
            "GITHUB_AGENT_MODEL", self.default_static_agent_model
        )
        self.documentation_agent_model: str = os.getenv(
            "DOCUMENTATION_AGENT_MODEL", self.default_static_agent_model
        )
        self.supervisor_max_parallel_agents: int = int(
            os.getenv("SUPERVISOR_MAX_PARALLEL_AGENTS", "3")
        )
        self.supervisor_tool_timeout: int = int(
            os.getenv("SUPERVISOR_TOOL_TIMEOUT", "30")
        )


settings = Settings()
