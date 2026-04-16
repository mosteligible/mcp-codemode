from config import settings
from tools import execute_code

from pydantic_ai import Agent, Tool

GithubAgent = Agent(
    name="GithubAgent",
    model="openai:gpt-5.3",
    instructions=f"""You are a helpful assistant that can interact with GitHub repositories. You have access to the following tools:
    1. Code Execution Tool: Allows you to execute code in an isolated environment. Use this tool to run scripts, analyze code, or perform any computations needed to assist the user.
    2. Network request: Through the code execution environment, you can make HTTP requests to GitHub's API to fetch repository information, issues, pull requests, etc. Network request will have to be made through a proxy server {settings.code_execution_host}/proxy.

    If there are pre-processing in the steps to get information from Github api, attempt to use the code execution tool to process the information instead of reading the whole api response and trying to extract relevant information.
    """,
    tool_timeout=15,  # Set a timeout for tool execution to prevent hanging
    retries=3,
    tools=[
        Tool(
            function=execute_code.execution_handler,
            name="execute_code",
        )
    ],
)
