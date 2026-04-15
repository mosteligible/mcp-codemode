from pydantic import BaseModel, Field


class CodeRunnerRequest(BaseModel):
    code: str = Field(..., description="The code to be executed")
    language: str = Field(
        default="python", description="The programming language of the code"
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID for stateful interactions",
        alias="sessionId",
    )


class CodeRunnerResponse(BaseModel):
    output: str = Field(
        ..., description="The combined stdout and stderr from code execution"
    )
    error: int = Field(..., description="Error message from code execution")
