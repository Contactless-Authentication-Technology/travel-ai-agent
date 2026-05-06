import json
from pathlib import Path
from request_loader import load_travel_request
from datetime import datetime


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


def save_payload(payload: dict, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parents[1]

    example_path = root_dir / "examples" / "paris_request.example.json"

    travel_request = load_travel_request(str(example_path))
    booking_payload = build_booking_com_payload(travel_request)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    latest_output_path = root_dir / "output" / "booking_payload_latest.json"
    history_output_path = root_dir / "output" / f"booking_payload_{timestamp}.json"

    save_payload(booking_payload, str(latest_output_path))
    save_payload(booking_payload, str(history_output_path))

    print(json.dumps(booking_payload, indent=2, ensure_ascii=False))
    print(f"\nSaved latest to: {latest_output_path}")
    print(f"Saved history to: {history_output_path}")