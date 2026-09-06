from pydantic import BaseModel

from agent_toolbox.adapter.inbound.enum.status import HealthStatus


class HealthSchema(BaseModel):
    status: HealthStatus


class InfoSchema(BaseModel):
    name: str
    version: str
    environment: str
    api_root_path: str
    authors: str
