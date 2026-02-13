# from tools.registry import code_interpreter
import time

from llm_sandbox import SandboxSession, SandboxBackend, SupportedLanguage
from llm_sandbox.pool import create_pool_manager, PoolConfig


# docker_pool = create_pool_manager(
#     backend=SandboxBackend.DOCKER,
#     config=PoolConfig(
#         max_pool_size=3,
#         min_pool_size=1,
#         enable_prewarming=True,
#     ),
#     lang="python",
# )


def run_code_stuff(language: SupportedLanguage, code: str) -> str:
    print(f" code: {code}")
    with SandboxSession(
        language=language,
        # pool=docker_pool,
        default_timeout=10,
        verbose=True,
        skip_environment_setup=True,
        container_id="423db6f8d65e",
    ) as session:
        result = session.run(code=code)
    print(f"{result.exit_code=}, {result.success()=}, {result.stderr=}")
    return result.stdout


def main(c: int):
    code = f"print('Hello, World! - {c}')"
    output = run_code_stuff(language=SupportedLanguage.PYTHON, code=code)
    print("Code Output:", output)


if __name__ == "__main__":
    count = 0
    while count < 2:
        count += 1
        main(count)
    # docker_pool.close()
