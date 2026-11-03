from pydantic import BaseModel, Field


class ExecutePythonInput(BaseModel):
    code: str = Field(
        description=(
            "Python source code to run in a sandbox. Assign your final value to a variable "
            "named 'result'; otherwise set result='no return'."
        )
    )
