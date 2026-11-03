from typing import Any

from pydantic import BaseModel

from agent_toolbox.application.port.outbound.tool_port import Tool

_JSON_TYPES: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "null": "None",
}


def call_signature(tool: Tool) -> str:
    schema: dict[str, Any] = tool.input_model.model_json_schema()
    definitions: dict[str, Any] = schema.get("$defs", {})
    required: set[str] = set(schema.get("required", ()))

    parameters: list[str] = []
    for name, field in schema.get("properties", {}).items():
        parameter = f"{name}: {_render(field, definitions)}"
        if name not in required:
            parameter += f" = {field.get('default')!r}"
        parameters.append(parameter)

    return f"{tool.name}(*, {', '.join(parameters)})" if parameters else f"{tool.name}()"


def return_shape(model: type[BaseModel]) -> str:
    schema: dict[str, Any] = model.model_json_schema()
    return _render(schema, schema.get("$defs", {}))


def python_stub(tool: Tool) -> str:
    lines: list[str] = [f"{call_signature(tool)} -> {return_shape(tool.output_model)}"]
    lines += [
        f"    {name}: {field.description}"
        for name, field in tool.input_model.model_fields.items()
        if field.description
    ]
    return "\n".join(lines)


def described(tool: Tool) -> str:
    return f"{tool.description}\n\nReturns: {return_shape(tool.output_model)}"


def _render(node: dict[str, Any], definitions: dict[str, Any]) -> str:
    if "$ref" in node:
        return _render(definitions[node["$ref"].rsplit("/", 1)[-1]], definitions)
    if "const" in node:
        return repr(node["const"])
    if "enum" in node:
        return " | ".join(repr(value) for value in node["enum"])
    for key in ("oneOf", "anyOf"):
        if key in node:
            return " | ".join(_render(option, definitions) for option in node[key])

    kind: Any = node.get("type")
    if kind == "object":
        return _render_object(node, definitions)
    if kind == "array":
        items: dict[str, Any] | None = node.get("items")
        return f"list[{_render(items, definitions)}]" if items else "list[Any]"
    return _JSON_TYPES.get(kind, "Any") if isinstance(kind, str) else "Any"


def _render_object(node: dict[str, Any], definitions: dict[str, Any]) -> str:
    properties: dict[str, Any] | None = node.get("properties")
    if properties:
        fields = (f"{name}: {_render(field, definitions)}" for name, field in properties.items())
        return "{" + ", ".join(fields) + "}"

    values: Any = node.get("additionalProperties")
    if isinstance(values, dict) and values:
        return f"dict[str, {_render(values, definitions)}]"
    return "dict[str, Any]"
