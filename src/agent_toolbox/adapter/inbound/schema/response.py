from pydantic import BaseModel

from agent_toolbox.adapter.inbound.enum.status import HealthStatus


class DependencySchema(BaseModel):
    status: HealthStatus
    since: str
    error: str | None = None


class HealthSchema(BaseModel):
    status: HealthStatus
    dependencies: dict[str, DependencySchema] | None = None


class InfoSchema(BaseModel):
    name: str
    version: str
    environment: str
    authors: str
