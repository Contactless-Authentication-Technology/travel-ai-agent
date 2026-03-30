from typing import Optional, Protocol, Union, runtime_checkable

from intents import Intent
from schemas import CreatePlanPayload, ModifyPlanPayload

ParsedPayload = Union[CreatePlanPayload, ModifyPlanPayload]


@runtime_checkable
class BaseParser(Protocol):
    intent: Intent

    def parse(self, message: str, context: Optional[dict] = None) -> ParsedPayload:
        ...
