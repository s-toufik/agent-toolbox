import os
from dataclasses import dataclass
from pathlib import Path

import dotenv


@dataclass(frozen=True, slots=True)
class ProcessSettings:
    role: str
    environment: str
    configuration_directory: Path
    log_level: str = "INFO"
    working_directory: Path | None = None
    sandbox_tool_access: bool = False

    @classmethod
    def for_role(cls, role: str) -> ProcessSettings:
        dotenv.load_dotenv()
        directory = os.getenv("CONFIGURATION_DIR", "./config")
        working_directory = os.getenv("WORKING_DIRECTORY")

        return cls(
            role=role,
            environment=os.getenv("APP_ENV", "debug"),
            configuration_directory=Path(directory),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            working_directory=Path(working_directory) if working_directory else None,
            sandbox_tool_access=os.getenv("SANDBOX_TOOL_ACCESS", "").lower()
            in ("true", "1", "yes", "on"),
        )
