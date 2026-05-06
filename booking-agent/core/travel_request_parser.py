import re
import json

def extract_dates(text: str) -> tuple[str, str]:
    pattern = r"(\d+)월\s*(\d+)일.*?(\d+)월\s*(\d+)일"

    match = re.search(pattern, text)

    if not match:
        return "2026-07-10", "2026-07-15"

    departure_month = int(match.group(1))
    departure_day = int(match.group(2))

    return_month = int(match.group(3))
    return_day = int(match.group(4))

    departure_date = (
        f"2026-{departure_month:02d}-{departure_day:02d}"
    )

    return_date = (
        f"2026-{return_month:02d}-{return_day:02d}"
    )

    return departure_date, return_date

def parse_travel_request(text: str) -> dict:
    departure_date, return_date = extract_dates(text)
 
    request = {
        "destination": "",
        "departureDate": departure_date,
        "returnDate": return_date,
        "adults": 1,
        "hotelPreference": []
    }

    if "파리" in text:
        request["destination"] = "Paris"

    adults_match = re.search(r"성인\s*(\d+)명", text)
    if adults_match:
        request["adults"] = int(adults_match.group(1))

    if "에펠탑" in text:
        request["hotelPreference"].append("near_eiffel_tower")

    if "조식" in text:
        request["hotelPreference"].append("breakfast_included")

    if "역세권" in text or "지하철" in text:
        request["hotelPreference"].append("near_metro")

    return request


if __name__ == "__main__":
    user_input = (
        "7월 10일부터 7월 15일까지 "
        "파리 여행 가고 싶어. "
        "성인 2명이고 에펠탑 근처 호텔이면 좋겠어."
    )

    travel_request = parse_travel_request(user_input)

    print(
        json.dumps(
            travel_request,
            indent=2,
            ensure_ascii=False
        )
    )