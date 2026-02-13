from fastapi import FastAPI
from llm_sandbox import SupportedLanguage

from tools.registry.code_interpreter import run_code_stuff

app = FastAPI()

@app.post("/run_code/")
def run_code(code: str):
    output = run_code_stuff(language=SupportedLanguage.PYTHON, code=code)
    return {"output": output}
