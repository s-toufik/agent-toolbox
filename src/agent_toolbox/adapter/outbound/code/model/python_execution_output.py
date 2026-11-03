from typing import Any

from pydantic import BaseModel, Field


class ExecutePythonOutput(BaseModel):
    result_type: str = Field(description="Python type name of the 'result' value.")
    result: Any = Field(
        description="The value assigned to 'result'. Values that aren't JSON-serializable are stringified."
    )
    stdout: str = Field(default="", description="Anything the code printed.")
