from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

core_path = Path(__file__).resolve().parents[1] / "core"
sys.path.append(str(core_path))

from booking_payload_builder import build_booking_com_payload
from travel_request_parser import parse_travel_request
from api_clients.kiwi import search_flights, search_price_calendar, city_to_iata

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SESSION_STATE = {
    "travelRequestText": "",
    "travelRequest": None,
    "payload": None,
    "flightResults": [],
    "recommendations": [],
    "roomOptions": [],
    "selectedHotelIndex": None,
    "lastCommand": None,
    "lastResult": None,
    "agentStatus": {
        "connected": False,
        "lastSeenAt": None,
        "url": None
    }
}

COMMAND_QUEUE = deque()

COMMAND_PAGE_RULES = {
    "RUN_BOOKING_FLOW": ["other", "search_results"],
    "GET_TOP_HOTEL_RECOMMENDATIONS": ["search_results"],
    "CLICK_BEST_MATCHED_HOTEL": ["search_results"],
    "CONFIRM_SPECIFIC_HOTEL_SELECTION": ["search_results"],
    "EXTRACT_ROOM_OPTIONS": ["hotel_detail"]
}


class TravelRequestInput(BaseModel):
    text: str


class CommandInput(BaseModel):
    action: str
    payload: dict = Field(default_factory=dict)


class CommandCompletion(BaseModel):
    result: dict = Field(default_factory=dict)


class SelectionUpdate(BaseModel):
    hotelIndex: int | None = None


class AgentHeartbeat(BaseModel):
    url: str
    status: str = "ready"


@app.get("/")
def get_dashboard() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.post("/parse")
def parse_request(request: TravelRequestInput):
    travel_request = parse_travel_request(request.text)
    booking_payload = build_booking_com_payload(travel_request)

    SESSION_STATE["travelRequestText"] = request.text
    SESSION_STATE["travelRequest"] = travel_request
    SESSION_STATE["payload"] = booking_payload

    return booking_payload


@app.post("/api/parse")
def parse_request_for_dashboard(request: TravelRequestInput):
    payload = parse_request(request)
    return {
        "ok": True,
        "travelRequest": deepcopy(SESSION_STATE["travelRequest"]),
        "payload": payload
    }


@app.post("/api/flights/price-calendar")
def price_calendar_endpoint():
    travel_request = SESSION_STATE.get("travelRequest")

    if not travel_request:
        return {"ok": False, "error": "먼저 여행 요청을 해석해 주세요."}

    origin_iata = city_to_iata(travel_request.get("origin", "서울"))
    destination_iata = city_to_iata(travel_request.get("destination", ""))

    if not origin_iata or not destination_iata:
        return {"ok": False, "error": "출발지 또는 목적지 IATA 코드를 찾을 수 없습니다."}

    departure_date = travel_request.get("departureDate", "")
    month = departure_date[:7] if departure_date else ""

    if not month:
        return {"ok": False, "error": "출발 날짜를 먼저 입력해 주세요."}

    try:
        calendar = search_price_calendar(
            fly_from=origin_iata,
            fly_to=destination_iata,
            month=month,
            adults=travel_request.get("adults", 1),
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "calendar": calendar}


@app.post("/api/flights/search")
def search_flights_endpoint():
    travel_request = SESSION_STATE.get("travelRequest")

    if not travel_request:
        return {"ok": False, "error": "먼저 여행 요청을 해석해 주세요."}

    origin_iata = city_to_iata(travel_request.get("origin", "서울"))
    destination_iata = city_to_iata(travel_request.get("destination", ""))

    if not origin_iata:
        return {"ok": False, "error": f"출발지 IATA 코드를 찾을 수 없습니다: {travel_request.get('origin')}"}

    if not destination_iata:
        return {"ok": False, "error": f"목적지 IATA 코드를 찾을 수 없습니다: {travel_request.get('destination')}"}

    try:
        flights = search_flights(
            fly_from=origin_iata,
            fly_to=destination_iata,
            departure_date=travel_request["departureDate"],
            return_date=travel_request.get("returnDate"),
            adults=travel_request.get("adults", 1),
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}

    SESSION_STATE["flightResults"] = flights
    return {"ok": True, "flights": flights}


@app.get("/api/session")
def get_session_state():
    return {
        "ok": True,
        "session": deepcopy(SESSION_STATE)
    }


@app.post("/api/session/selection")
def update_selection(selection: SelectionUpdate):
    SESSION_STATE["selectedHotelIndex"] = selection.hotelIndex
    return {
        "ok": True,
        "selectedHotelIndex": SESSION_STATE["selectedHotelIndex"]
    }


@app.post("/api/agent/heartbeat")
def update_agent_heartbeat(heartbeat: AgentHeartbeat):
    SESSION_STATE["agentStatus"] = {
        "connected": True,
        "lastSeenAt": utc_now_iso(),
        "url": heartbeat.url,
        "status": heartbeat.status
    }
    return {"ok": True}


@app.post("/api/commands")
def enqueue_command(command: CommandInput):
    command_record = {
        "id": str(uuid4()),
        "action": command.action,
        "payload": command.payload,
        "status": "pending",
        "createdAt": utc_now_iso()
    }
    COMMAND_QUEUE.append(command_record)
    return {
        "ok": True,
        "command": deepcopy(command_record)
    }


@app.get("/api/commands/next")
def get_next_command(page_type: str = Query(default="other")):
    if not COMMAND_QUEUE:
        return {
            "ok": True,
            "command": None
        }

    matched_index = None

    for index, command in enumerate(COMMAND_QUEUE):
        allowed_page_types = COMMAND_PAGE_RULES.get(command["action"])

        if not allowed_page_types or page_type in allowed_page_types:
            matched_index = index
            break

    if matched_index is None:
        return {
            "ok": True,
            "command": None
        }

    command = COMMAND_QUEUE[matched_index]
    del COMMAND_QUEUE[matched_index]
    command["status"] = "in_progress"
    return {
        "ok": True,
        "command": deepcopy(command)
    }


@app.post("/api/commands/{command_id}/complete")
def complete_command(command_id: str, completion: CommandCompletion):
    command_action = completion.result.get("action")
    command_response = completion.result.get("response", {})

    SESSION_STATE["lastCommand"] = {
        "id": command_id,
        "action": command_action,
        "completedAt": utc_now_iso()
    }
    SESSION_STATE["lastResult"] = deepcopy(completion.result)

    if (
        command_action == "GET_TOP_HOTEL_RECOMMENDATIONS" and
        command_response.get("ok")
    ):
        SESSION_STATE["recommendations"] = deepcopy(
            command_response.get("recommendations", [])
        )
        SESSION_STATE["selectedHotelIndex"] = command_response.get(
            "recommendedHotelIndex"
        )

    if (
        command_action == "CLICK_BEST_MATCHED_HOTEL" and
        command_response.get("ok")
    ):
        SESSION_STATE["selectedHotelIndex"] = command_response.get("hotelIndex")

    if (
        command_action == "EXTRACT_ROOM_OPTIONS" and
        command_response.get("ok")
    ):
        SESSION_STATE["roomOptions"] = deepcopy(
            command_response.get("roomOptions", [])
        )

    if command_action == "CONFIRM_SPECIFIC_HOTEL_SELECTION":
        SESSION_STATE["selectedHotelIndex"] = completion.result.get(
            "payload",
            {}
        ).get("hotelIndex")

    return {"ok": True}
