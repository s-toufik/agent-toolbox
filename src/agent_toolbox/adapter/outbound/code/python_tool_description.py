from dataclasses import dataclass

LEAD_WITH_TOOLS: str = (
    "Run Python in a sandbox for heavy analysis and bulk tool calls: the other tools are "
    "functions inside the code, and their results stay out of your context."
)
LEAD_ALONE: str = "Run Python in a sandbox for heavy analysis and computation."

_CALLING: tuple[str, ...] = (
    "Call a tool as a function with keyword arguments: it returns what a direct call returns, "
    "as dicts and lists, and raises ToolError when the call fails.",
    "Use it for heavy work: many tool calls or one tool many times, large files, joins, "
    "aggregation, statistics. Return a summary or a file path, not the raw data.",
    "Learn a tool's data shape before coding on it: one direct call with a small limit, or a "
    "short script that returns a single item.",
    "Pass plain JSON values as arguments: convert a DataFrame with "
    "json.loads(df.to_json(orient='records', date_format='iso')) and a NumPy number with "
    ".item().",
)
_ALONE: tuple[str, ...] = (
    "Use it for heavy work: large files, joins, aggregation, statistics. Return a summary or "
    "a file path, not the raw data.",
)


@dataclass(frozen=True, slots=True)
class PythonToolDescription:
    allowed_modules: tuple[str, ...]
    timeout_seconds: int
    working_directory: str | None = None
    callable_tools: tuple[str, ...] = ()

    def render(self) -> str:
        lines: list[str] = [LEAD_WITH_TOOLS if self.callable_tools else LEAD_ALONE]
        lines += [f"- {line}" for line in (_CALLING if self.callable_tools else _ALONE)]
        lines.append(
            "- Assign the final value to 'result' (result='no return' when there is none); what "
            f"the code prints comes back too. Timeout: {self.timeout_seconds} seconds."
        )
        if self.working_directory:
            lines.append(
                f"- Files: {self.working_directory} is the code's current directory, also in "
                "WORKING_DIRECTORY. Use relative paths: the file tools resolve them the same "
                "way. Access outside it is denied."
            )
        lines.append(f"Modules: {', '.join(self.allowed_modules)}.")
        if self.callable_tools:
            lines.append(f"Tools callable in code: {', '.join(self.callable_tools)}.")
        return "\n".join(lines)
