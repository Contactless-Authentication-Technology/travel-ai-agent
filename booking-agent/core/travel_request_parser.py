import re
import json

ORIGIN_CITIES = {
    "서울": "서울",
    "인천": "인천",
    "김포": "김포",
    "부산": "부산",
    "제주": "제주",
    "대구": "대구",
    "청주": "청주",
}

def extract_origin(text: str) -> str:
    pattern = r"(" + "|".join(ORIGIN_CITIES.keys()) + r")에서"
    match = re.search(pattern, text)
    if match:
        return match.group(1)

    for city in ORIGIN_CITIES:
        if f"{city} 출발" in text:
            return city

    return "서울"

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

def contains_any_keyword(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)

def add_preference_if_matched(
    preferences: list[str],
    text: str,
    preference: str,
    keywords: list[str]
) -> None:
    if contains_any_keyword(text, keywords) and preference not in preferences:
        preferences.append(preference)

def parse_travel_request(text: str) -> dict:
    departure_date, return_date = extract_dates(text)
 
    origin = extract_origin(text)

    request = {
        "origin": origin,
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

    add_preference_if_matched(
        request["hotelPreference"],
        text,
        "near_eiffel_tower",
        [
            "에펠탑",
            "에펠 타워",
            "eiffel",
            "에펠탑 근처",
            "에펠탑 가까운",
            "에펠탑 주변"
        ]
    )

    add_preference_if_matched(
        request["hotelPreference"],
        text,
        "breakfast_included",
        [
            "조식",
            "조식 포함",
            "아침 포함",
            "아침 제공",
            "breakfast",
            "breakfast included",
            "free breakfast"
        ]
    )

    add_preference_if_matched(
        request["hotelPreference"],
        text,
        "near_metro",
        [
            "역세권",
            "지하철",
            "지하철 가까운",
            "지하철 근처",
            "역 근처",
            "metro",
            "subway"
        ]
    )

    add_preference_if_matched(
        request["hotelPreference"],
        text,
        "value_for_money",
        [
            "가성비",
            "가성비 좋은",
            "가격 대비",
            "합리적인 가격",
            "저렴한데 좋은",
            "budget friendly",
            "value for money",
            "affordable"
        ]
    )

    add_preference_if_matched(
        request["hotelPreference"],
        text,
        "high_review_score",
        [
            "높은 평점",
            "평점이 높은",
            "리뷰 좋은",
            "후기 좋은",
            "review score",
            "high rating",
            "high review"
        ]
    )

    add_preference_if_matched(
        request["hotelPreference"],
        text,
        "luxury_stay",
        [
            "럭셔리",
            "고급",
            "고급스러운",
            "5성급",
            "호캉스",

            "luxury",
            "premium",
            "upscale"
        ]
    )

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
