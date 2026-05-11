from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path

core_path = Path(__file__).resolve().parents[1] / "core"
sys.path.append(str(core_path))

from travel_request_parser import parse_travel_request
from booking_payload_builder import build_booking_com_payload

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TravelRequest(BaseModel):
    text: str


@app.post("/parse")
def parse_request(request: TravelRequest):
    travel_request = parse_travel_request(request.text)
    booking_payload = build_booking_com_payload(travel_request)
    return booking_payload