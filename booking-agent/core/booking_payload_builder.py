import json
from pathlib import Path
from request_loader import load_travel_request


def build_booking_com_payload(travel_request: dict) -> dict:
    return {
        "site": "booking.com",
        "payload": {
            "destination": travel_request["destination"],
            "checkIn": travel_request["departureDate"],
            "checkOut": travel_request["returnDate"],
            "adults": travel_request["adults"]
        }
    }


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parents[1]
    example_path = root_dir / "examples" / "paris_request.example.json"

    travel_request = load_travel_request(str(example_path))
    booking_payload = build_booking_com_payload(travel_request)

    print(json.dumps(booking_payload, indent=2, ensure_ascii=False))