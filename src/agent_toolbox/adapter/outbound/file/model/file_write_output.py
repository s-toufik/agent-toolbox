from pydantic import BaseModel, Field


class WriteFileOutput(BaseModel):
    path: str = Field(description="Absolute path the data was written to.")
