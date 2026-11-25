import copy
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, create_model, model_validator
from pydantic_core import ErrorDetails

from agent_toolbox.application.port.outbound.tool_port import Tool
from agent_toolbox.domain.exception.tool_failure import ToolFailure
from agent_toolbox.domain.model.tool_scope import ToolAlias


class AliasedTool(Tool[BaseModel, BaseModel]):
    def __init__(self, alias: ToolAlias, target: Tool) -> None:
        _check_fixed(alias, target)
        self.alias = alias
        self.target = target
        self.name = alias.name
        self.description = alias.description or target.description
        self.input_model = _input_without_fixed(alias, target)
        self.output_model = target.output_model

    async def run(self, arguments: BaseModel) -> BaseModel:
        merged: dict[str, Any] = arguments.model_dump(exclude_unset=True) | copy.deepcopy(
            dict(self.alias.fixed)
        )
        try:
            validated: BaseModel = self.target.input_model.model_validate(merged)
        except ValidationError as error:
            raise ToolFailure(
                f"'{self.name}' could not call '{self.target.name}': {_problems(error.errors())}"
            ) from error
        return await self.target.run(validated)


def _check_fixed(alias: ToolAlias, target: Tool) -> None:
    model: type[BaseModel] = target.input_model
    unknown: list[str] = sorted(set(alias.fixed) - model.model_fields.keys())
    if unknown and model.model_config.get("extra") != "allow":
        raise ValueError(
            f"alias '{alias.name}': '{target.name}' has no argument {', '.join(unknown)}"
        )
    try:
        model.model_validate(dict(alias.fixed))
    except ValidationError as error:
        wrong: list[ErrorDetails] = [
            detail
            for detail in error.errors()
            if detail["type"] != "missing" and detail["loc"] and detail["loc"][0] in alias.fixed
        ]
        if wrong:
            raise ValueError(
                f"alias '{alias.name}': fixed arguments don't fit '{target.name}': "
                f"{_problems(wrong)}"
            ) from error


def _input_without_fixed(alias: ToolAlias, target: Tool) -> type[BaseModel]:
    fixed: frozenset[str] = frozenset(alias.fixed)

    def refuse_fixed(cls: type[BaseModel], data: Any) -> Any:
        if isinstance(data, Mapping):
            given: list[str] = sorted(fixed & data.keys())
            if given:
                verb: str = "is" if len(given) == 1 else "are"
                raise ValueError(f"{', '.join(given)} {verb} fixed by '{alias.name}'")
        return data

    config: ConfigDict = target.input_model.model_config.copy()
    config.pop("title", None)
    fields: dict[str, Any] = {
        name: (info.annotation, info)
        for name, info in target.input_model.model_fields.items()
        if name not in fixed
    }
    validators: dict[str, Any] = {"_refuse_fixed": model_validator(mode="before")(refuse_fixed)}
    return create_model(
        f"{alias.name}_input", __config__=config, __validators__=validators, **fields
    )


def _problems(details: list[ErrorDetails]) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in detail['loc']) or 'arguments'}: {detail['msg']}"
        for detail in details
    )
