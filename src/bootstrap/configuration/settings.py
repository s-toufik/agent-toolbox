import os
from dataclasses import dataclass
from pathlib import Path

import dotenv


@dataclass(frozen=True, slots=True)
class ProcessSettings:
    role: str
    environment: str
    configuration_directory: Path
    vault_directory: Path | None = None
    sandbox_tool_access: bool = False

    @classmethod
    def for_role(cls, role: str) -> ProcessSettings:
        dotenv.load_dotenv()
        directory = os.getenv("CONFIGURATION_DIR", "./config")
        vault_directory = os.getenv("SANDBOX_VAULT_DIR")

        return cls(
            role=role,
            environment=os.getenv("APP_ENV", "debug"),
            configuration_directory=Path(directory),
            vault_directory=Path(vault_directory) if vault_directory else None,
            sandbox_tool_access=os.getenv("SANDBOX_TOOL_ACCESS", "").lower()
            in ("true", "1", "yes", "on"),
        )
