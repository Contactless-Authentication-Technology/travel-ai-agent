from uuid import uuid4

from fastapi import HTTPException
from typing import Optional

from intents import Intent
from parsers.classifier import extract_intent
from parsers.llm import LLMStructuredOutputError
from parsers.registry import parser_registry
from schemas import AgentRunRequest, AgentRunResponse, Clarify

# MVP in-memory trip state 저장소
TRIP_STATE: dict[str, dict] = {}

def _run_create_plan_mcp(plan_payload: dict) -> tuple[str, dict]:
    trip_id = str(uuid4())  # uuid란 랜덤한 고유 id를 만드는 함수
    trip_state = {
        "intent": Intent.CREATE_PLAN.value,
        "plan": plan_payload,
        "meta": {"mcp": "stub"},
    }
    TRIP_STATE[trip_id] = trip_state
    return trip_id, trip_state


def _run_modify_plan_mcp(modify_payload: dict) -> tuple[str, dict]:
    trip_id = str(modify_payload.get("trip_id") or uuid4())
    trip_state = {
        "intent": Intent.MODIFY_PLAN.value,
        "modify": modify_payload,
        "meta": {"mcp": "stub"},
    }
    TRIP_STATE[trip_id] = trip_state
    return trip_id, trip_state


MCP_RUNNERS = {
    Intent.CREATE_PLAN: _run_create_plan_mcp,
    Intent.MODIFY_PLAN: _run_modify_plan_mcp,
}

PAYLOAD_DATA_KEYS = {
    Intent.CREATE_PLAN: "plan",
    Intent.MODIFY_PLAN: "modify",
}


def _build_clarify(parsed_payload: object) -> Clarify:
    clarify = getattr(parsed_payload, "clarify")
    return Clarify(
        needed=clarify.needed,
        missing_fields=list(clarify.missing_fields),
    )


def _response_trip_id(intent: Intent, parsed_payload: object) -> str:
    if intent is Intent.MODIFY_PLAN:
        return str(getattr(parsed_payload, "trip_id", "") or "")
    return ""


def _strip_clarify(payload_dict: dict) -> dict:
    payload = dict(payload_dict)
    payload.pop("clarify", None)
    return payload


def agent_run(payload: AgentRunRequest) -> AgentRunResponse:
    try:
        intent = extract_intent(payload.message, payload.context)
        parser = parser_registry.get(intent)

        if parser is None:
            return AgentRunResponse(
                status="ERROR",
                intent=intent.value,
                trip_id="",
                data={"code": "NOT_IMPLEMENTED", "message": f"{intent.value} is not implemented yet."},
                clarify=Clarify(needed=False, missing_fields=[]),
            )

        parsed_payload = parser.parse(payload.message, payload.context)
        clarify = _build_clarify(parsed_payload)
        payload_dict = _strip_clarify(parsed_payload.model_dump())
        data_key = PAYLOAD_DATA_KEYS[intent]

        if clarify.needed:
            return AgentRunResponse(
                status="ASK",
                intent=parsed_payload.intent,
                trip_id=_response_trip_id(intent, parsed_payload),
                data={data_key: payload_dict},
                clarify=clarify,
            )

        trip_id, trip_state = MCP_RUNNERS[intent](parsed_payload.model_dump())
        if isinstance(trip_state.get(data_key), dict):
            trip_state[data_key].pop("clarify", None)
        return AgentRunResponse(
            status="DONE",
            intent=parsed_payload.intent,
            trip_id=trip_id,
            data=trip_state,
            clarify=clarify,
        )

    except LLMStructuredOutputError as exc:
        raise HTTPException(status_code=500, detail=f"Parser failed: {exc}") from exc
