import os
from dataclasses import dataclass, field
from pathlib import Path

import dotenv


@dataclass(frozen=True, slots=True)
class ProcessSettings:
    role: str
    environment: str
    configuration_directory: Path
    working_directory: Path | None = None
    sandbox_tool_access: bool = False
    jwt_key: str | None = field(default=None, repr=False)
    jwt_username: str | None = None
    deployment_environment: str = "unknown"
    extra_allowed_hosts: tuple[str, ...] = ()

    @classmethod
    def for_role(cls, role: str) -> ProcessSettings:
        dotenv.load_dotenv()
        working_directory = os.getenv("WORKING_DIRECTORY")
        return cls(
            role=role,
            environment=os.getenv("APP_ENV", "debug"),
            configuration_directory=Path(os.getenv("CONFIGURATION_DIR", "./config")),
            working_directory=Path(working_directory) if working_directory else None,
            sandbox_tool_access=os.getenv("SANDBOX_TOOL_ACCESS", "").lower()
            in ("true", "1", "yes", "on"),
            jwt_key=os.getenv("JWT_KEY") or None,
            jwt_username=os.getenv("JWT_USERNAME") or None,
            deployment_environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "unknown"),
            extra_allowed_hosts=tuple(
                host.strip()
                for host in os.getenv("TOOLBOX_EXTRA_ALLOWED_HOSTS", "").split(",")
                if host.strip()
            ),
        )
