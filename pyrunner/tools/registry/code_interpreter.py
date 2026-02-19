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
    with SandboxSession(
        language=language,
        container_id="468271fc9792",
    ) as session:
        result = session.run(code=code)
    return result.stdout, result.stderr, result.exit_code, result.success()
