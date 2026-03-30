from intents import Intent
from parsers.base import BaseParser


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[Intent, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        self._parsers[parser.intent] = parser

    def get(self, intent: Intent) -> BaseParser | None:
        return self._parsers.get(intent)

    def has(self, intent: Intent) -> bool:
        return intent in self._parsers

    def registered_intents(self) -> tuple[Intent, ...]:
        return tuple(self._parsers.keys())


def build_default_parser_registry() -> ParserRegistry:
    registry = ParserRegistry()

    from parsers.create_plan.parser import CreatePlanParser
    from parsers.modify_plan.parser import ModifyPlanParser

    registry.register(CreatePlanParser())
    registry.register(ModifyPlanParser())
    return registry


parser_registry = build_default_parser_registry()
