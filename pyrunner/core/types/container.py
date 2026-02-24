from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ContainerInfo:
    id: str
    name: str
    image: str
    status: str


@dataclass
class CodeExecResult:
    stdout: str
    stderr: str
    exit_code: int
    truncated: bool = False


@dataclass
class FileContent:
    path: str
    content: str
    encoding: str = "utf-8"
