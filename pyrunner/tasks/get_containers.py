import docker
from core.types.container import ContainerInfo

def get_containers() -> list[ContainerInfo]:
    client = docker.from_env()
    containers = client.containers.list()
    container_info = []
    for container in containers:
        info = ContainerInfo(
            id=container.id,
            name=container.name,
            status=container.status,
            image=container.image.tags[0] if container.image.tags else 'N/A'
        )
        container_info.append(info)
    return container_info
