import re
from dataclasses import dataclass
from datetime import timedelta

NEVER: str = "never"
_DURATION = re.compile(r"(\d+)([mhd])")
_UNITS: dict[str, str] = {"m": "minutes", "h": "hours", "d": "days"}


@dataclass(frozen=True, slots=True)
class TokenLifetime:
    duration: timedelta | None

    @classmethod
    def parse(cls, expire: str) -> TokenLifetime:
        value: str = expire.strip().lower()
        if value == NEVER:
            return cls(None)
        match: re.Match[str] | None = _DURATION.fullmatch(value)
        if match is None or int(match.group(1)) == 0:
            raise ValueError(
                f"expire {expire!r} must be '{NEVER}' or a positive number of minutes, hours "
                "or days, such as '30m', '12h' or '7d'"
            )
        return cls(timedelta(**{_UNITS[match.group(2)]: int(match.group(1))}))


DEFAULT_TOKEN_LIFETIME: TokenLifetime = TokenLifetime(timedelta(hours=5))
