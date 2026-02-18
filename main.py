import subprocess
import random
from threading import Thread
from fastapi import FastAPI
from pydantic import BaseModel
from tasks.get_containers import get_containers

from tools.registry.code_interpreter import run_code_stuff


async def lifecycle():
    yield


app = FastAPI(
    lifecycle=lifecycle,
    title="Code Interpreter API",
)

class CodeRequest(BaseModel):
    code: str


@app.post("/run_code/")
def run_code(request: CodeRequest):
    print(f"Received code: {request.code}")
    container_id = random.choice(get_containers()).id
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-it",
            container_id,
            "python",
             "-c",
            request.code
        ],
        capture_output=True,
        text=True
    )
    return {
        "output": result.stdout,
        "error": result.stderr,
        "exit_code": result.returncode,
        "success": result.returncode == 0
    }
