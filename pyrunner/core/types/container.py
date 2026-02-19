from dataclasses import dataclass


@dataclass
class ContainerInfo:
    id: str
    name: str
    image: str
    status: str
