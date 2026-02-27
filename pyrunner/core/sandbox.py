from __future__ import annotations

import asyncio
import io
import logging
import tarfile
import posixpath
from typing import Any

import docker
from docker.models.containers import Container

from config import settings
from core.types.container import CodeExecResult

logger = logging.getLogger(__name__)

LANGUAGE_COMMANDS: dict[str, list[str]] = {
    "python": ["python", "-c"],
    "bash": ["bash", "-c"],
    "sh": ["sh", "-c"],
    "node": ["node", "-e"],
    "javascript": ["node", "-e"],
}


class SandboxPool:
    """Manages a pool of pre-spawned Docker containers for sandboxed code execution.

    Containers are created on startup with resource limits and network isolation.
    They are reused across calls via an asyncio.Queue-based acquire/release pattern.

    Designed for local Docker today; the interface can be adapted for remote
    Docker hosts or SSH-based execution in the future.
    """

    def __init__(self) -> None:
        self._client: docker.DockerClient | None = None
        self._queue: asyncio.Queue[Container] = asyncio.Queue()
        self._containers: list[Container] = []

    async def start(self) -> None:
        """Pull the sandbox image and spin up the container pool."""
        loop = asyncio.get_event_loop()
        self._client = docker.from_env()

        # Pull image only if not already present locally (blocking calls, run in executor)
        try:
            print(f" Checking for local sandbox image: {settings.sandbox_image}")
            res = self._client.images.get(settings.sandbox_image)
            print(f" Found local sandbox image: {res.tags}")
            logger.info("Using local sandbox image: %s", settings.sandbox_image)
        except docker.errors.ImageNotFound:
            logger.info("Pulling sandbox image: %s", settings.sandbox_image)
            await loop.run_in_executor(None, self._client.images.pull, settings.sandbox_image)

        # Calculate CPU quota from the cpu_limit (fraction of a CPU)
        cpu_period = 100_000  # microseconds (default)
        cpu_quota = int(settings.container_cpu_limit * cpu_period)

        for i in range(settings.pool_size):
            logger.info("Creating sandbox container %d/%d", i + 1, settings.pool_size)
            container: Container = await loop.run_in_executor(
                None,
                lambda: self._client.containers.run(  # type: ignore[union-attr]
                    image=settings.sandbox_image,
                    command="sleep infinity",
                    detach=True,
                    mem_limit=settings.container_memory_limit,
                    cpu_period=cpu_period,
                    cpu_quota=cpu_quota,
                    network_mode="bridge",
                    working_dir="/workspace",
                    stdin_open=True,
                    labels={"mcp-codemode": "sandbox"},
                    extra_hosts={"host.docker.internal": "host-gateway"},
                ),
            )
            # Ensure /workspace exists
            await loop.run_in_executor(
                None,
                lambda c=container: c.exec_run("mkdir -p /workspace"),
            )
            self._containers.append(container)
            await self._queue.put(container)

        logger.info("Sandbox pool ready with %d containers", settings.pool_size)

    async def shutdown(self) -> None:
        """Stop and remove all pooled containers."""
        loop = asyncio.get_event_loop()
        for container in self._containers:
            try:
                logger.info("Removing sandbox container %s", container.short_id)
                await loop.run_in_executor(
                    None, lambda c=container: c.remove(force=True)
                )
            except Exception:
                logger.exception("Failed to remove container %s", container.short_id)
        self._containers.clear()
        # Drain the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        if self._client:
            self._client.close()
            self._client = None
        logger.info("Sandbox pool shut down")

    async def acquire(self) -> Container:
        """Get a container from the pool. Blocks if none are available."""
        return await self._queue.get()

    async def release(self, container: Container) -> None:
        """Return a container to the pool.

        The /workspace directory is intentionally **not** cleaned between calls
        so that multi-step workflows (write file → execute code that reads it)
        work as expected.  Use :meth:`reset_workspace` for explicit cleanup.
        """
        await self._queue.put(container)

    async def reset_workspace(self, container: Container) -> None:
        """Remove all files from /workspace inside the container."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: container.exec_run(
                    ["sh", "-c", "rm -rf /workspace/* /workspace/.* 2>/dev/null || true"]
                ),
            )
        except Exception:
            logger.exception("Failed to clean workspace in container %s", container.short_id)

    async def exec_code(
        self,
        container: Container,
        code: str,
        language: str = "python",
        timeout: int | None = None,
    ) -> CodeExecResult:
        """Execute code inside the container and return the result.

        Args:
            container: The Docker container to execute in.
            code: Source code to run.
            language: Programming language (python, bash, sh, node, javascript).
            timeout: Max seconds to wait. Defaults to settings.exec_timeout.

        Returns:
            CodeExecResult with stdout, stderr, exit_code, and truncated flag.
        """
        if timeout is None:
            timeout = settings.exec_timeout

        cmd_prefix = LANGUAGE_COMMANDS.get(language.lower())
        if cmd_prefix is None:
            return CodeExecResult(
                stdout="",
                stderr=f"Unsupported language: {language}. Supported: {', '.join(LANGUAGE_COMMANDS)}",
                exit_code=1,
            )

        cmd = cmd_prefix + [code]
        loop = asyncio.get_event_loop()

        try:
            exit_code, output = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: container.exec_run(
                        cmd,
                        workdir="/workspace",
                        demux=True,
                    ),
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            # Kill any lingering process — best-effort
            try:
                await loop.run_in_executor(
                    None,
                    lambda: container.exec_run(["pkill", "-f", cmd_prefix[0]]),
                )
            except Exception:
                pass
            return CodeExecResult(
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                exit_code=-1,
            )

        stdout_raw, stderr_raw = output if output else (None, None)
        stdout = (stdout_raw or b"").decode("utf-8", errors="replace")
        stderr = (stderr_raw or b"").decode("utf-8", errors="replace")

        truncated = False
        if len(stdout) > settings.max_output_size:
            stdout = stdout[: settings.max_output_size] + "\n... [output truncated]"
            truncated = True
        if len(stderr) > settings.max_output_size:
            stderr = stderr[: settings.max_output_size] + "\n... [output truncated]"
            truncated = True

        return CodeExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            truncated=truncated,
        )

    # ── File I/O helpers ─────────────────────────────────────────────

    async def file_read(self, container: Container, path: str) -> bytes:
        """Read a file from the container.

        Returns the raw file bytes.  Raises FileNotFoundError on missing files.
        """
        loop = asyncio.get_event_loop()

        def _read() -> bytes:
            try:
                bits, _ = container.get_archive(path)
            except docker.errors.NotFound:
                raise FileNotFoundError(f"File not found in sandbox: {path}")
            # get_archive returns a tar stream — extract the single file
            stream = io.BytesIO(b"".join(bits))
            with tarfile.open(fileobj=stream) as tar:
                member = tar.getmembers()[0]
                f = tar.extractfile(member)
                if f is None:
                    raise IsADirectoryError(f"Path is a directory: {path}")
                return f.read()

        return await loop.run_in_executor(None, _read)

    async def file_write(self, container: Container, path: str, content: bytes) -> int:
        """Write content to a file inside the container.

        Creates parent directories as needed. Returns bytes written.
        """
        loop = asyncio.get_event_loop()

        def _write() -> int:
            # Ensure parent directory exists
            parent = posixpath.dirname(path)
            if parent:
                container.exec_run(["mkdir", "-p", parent])

            # Build an in-memory tar with the file
            tarstream = io.BytesIO()
            filename = posixpath.basename(path)
            with tarfile.open(fileobj=tarstream, mode="w") as tar:
                info = tarfile.TarInfo(name=filename)
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
            tarstream.seek(0)
            container.put_archive(parent or "/", tarstream)
            return len(content)

        return await loop.run_in_executor(None, _write)

    async def file_list(self, container: Container, path: str) -> str:
        """List directory contents inside the container. Returns ls -la output."""
        loop = asyncio.get_event_loop()
        exit_code, output = await loop.run_in_executor(
            None,
            lambda: container.exec_run(["ls", "-la", path], demux=True),
        )
        stdout_raw, stderr_raw = output if output else (None, None)
        if exit_code != 0:
            err = (stderr_raw or b"").decode("utf-8", errors="replace")
            raise FileNotFoundError(f"Cannot list path: {path}: {err}")
        return (stdout_raw or b"").decode("utf-8", errors="replace")


# Singleton instance — started/stopped by the application lifespan in main.py.
pool = SandboxPool()
