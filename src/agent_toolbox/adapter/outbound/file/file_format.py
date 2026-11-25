from pathlib import PurePath

DOCUMENT_FORMATS: tuple[str, ...] = ("json", "yml", "yaml")
TABLE_FORMATS: tuple[str, ...] = ("csv", "xlsx", "xls", "parquet")
TEXT_FORMATS: tuple[str, ...] = ("md", "txt", "svg")
BINARY_FORMATS: frozenset[str] = frozenset({"xlsx", "xls", "parquet"})
READ_ONLY_FORMATS: frozenset[str] = frozenset({"xls"})


def extension(file_path: str) -> str:
    return PurePath(file_path).suffix.lstrip(".").lower()


def listed(formats: tuple[str, ...], leaving_out: frozenset[str] = frozenset()) -> str:
    return ", ".join(name for name in formats if name not in leaving_out)
