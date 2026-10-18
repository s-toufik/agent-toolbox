from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model

_PYTHON_TYPES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "null": type(None),
}


def model_from_schema(model_name: str, schema: dict[str, Any] | None) -> type[BaseModel]:
    if not schema or schema.get("type") != "object" or not schema.get("properties"):
        return create_model(model_name, __config__=ConfigDict(extra="allow"))

    required: set[str] = set(schema.get("required", ()))
    fields: dict[str, Any] = {}
    for name, spec in schema["properties"].items():
        annotation = _annotation(spec)
        description = spec.get("description")
        if name in required:
            fields[name] = (annotation, Field(description=description))
        else:
            fields[name] = (
                annotation | None,
                Field(default=spec.get("default"), description=description),
            )
    return create_model(model_name, **fields)


def _annotation(spec: dict[str, Any]) -> Any:
    kind = spec.get("type")
    if kind == "array":
        items = spec.get("items")
        element_type = _annotation(items) if isinstance(items, dict) else Any
        return list[element_type]
    if kind == "object":
        return dict[str, Any]
    if isinstance(kind, list):
        concrete = [entry for entry in kind if entry != "null"]
        base = _PYTHON_TYPES.get(concrete[0], Any) if concrete else Any
        return base | None if "null" in kind else base
    return _PYTHON_TYPES.get(kind, Any)
