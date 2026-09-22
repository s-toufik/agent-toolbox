from typing import Any

from pydantic import BaseModel, Field


class PythonExecutionResult(BaseModel):
    result_type: str = Field(description="Python type name of the sandboxed 'result' value.")
    result: Any = Field(
        description=(
            "The value assigned to 'result' in the sandbox. Values that aren't natively "
            "JSON-serializable were stringified by the sandbox before being sent back."
        )
    )
