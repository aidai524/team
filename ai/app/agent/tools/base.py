"""Base tool interface, execution context, and a function-wrapper implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from app.plane.client import PlaneClient

if TYPE_CHECKING:
    from app.retrieval.service import RetrievalService


@dataclass
class ToolContext:
    """Dependencies available to every tool during execution."""

    plane: PlaneClient
    workspace_slug: str
    retrieval: "RetrievalService | None" = None


class Tool(ABC):
    """A callable capability exposed to the LLM via function calling."""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    async def execute(self, context: ToolContext, **kwargs: Any) -> str:
        """Run the tool and return a string for the model to consume."""
        raise NotImplementedError

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


ToolFn = Callable[..., Awaitable[str]]


class FunctionTool(Tool):
    """Adapter that turns a plain async function into a Tool."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        fn: ToolFn,
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters
        self._fn = fn

    async def execute(self, context: ToolContext, **kwargs: Any) -> str:
        return await self._fn(context, **kwargs)
