from abc import ABC, abstractmethod

from pydantic import BaseModel


class Tool[I: BaseModel, O: BaseModel](ABC):

    name: str
    description: str
    input_model: type[I]
    output_model: type[O]

    @abstractmethod
    async def run(self, arguments: I) -> O: ...
