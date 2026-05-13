import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """\
You are a travel request parser. Read the user's Korean or English travel request and output ONLY a JSON object.

Fields:
- origin: Korean city of departure (e.g. "서울", "부산", "인천"). Default "서울".
- destination: English city name (e.g. "Paris", "Tokyo", "New York", "Barcelona", "Rome", "Amsterdam").
- departureDate: YYYY-MM-DD. If year is not given, use 2026.
- returnDate: YYYY-MM-DD. If year is not given, use 2026.
- adults: number of adults as integer. Default 1.
- hotelPreference: list of applicable tags (use only from this set):
    "near_eiffel_tower" — near Eiffel Tower
    "breakfast_included" — breakfast included
    "near_metro" — near subway or metro station
    "value_for_money" — good value / affordable
    "high_review_score" — high rating / good reviews
    "luxury_stay" — luxury, 5-star, premium

Output only a valid JSON object. No prose, no markdown.
"""


def _parse_with_llm(text: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        max_tokens=400,
    )
    return json.loads(resp.choices[0].message.content)


def _parse_with_regex(text: str) -> dict:
    def extract_origin(t: str) -> str:
        cities = ["서울", "인천", "김포", "부산", "제주", "대구", "청주"]
        for city in cities:
            if f"{city}에서" in t or f"{city} 출발" in t:
                return city
        return "서울"

    def extract_dates(t: str) -> tuple[str, str]:
        match = re.search(r"(\d+)월\s*(\d+)일.*?(\d+)월\s*(\d+)일", t)
        if not match:
            return "2026-07-10", "2026-07-15"
        dep = f"2026-{int(match.group(1)):02d}-{int(match.group(2)):02d}"
        ret = f"2026-{int(match.group(3)):02d}-{int(match.group(4)):02d}"
        return dep, ret

    DEST_MAP = {
        "파리": "Paris", "도쿄": "Tokyo", "오사카": "Osaka",
        "뉴욕": "New York", "런던": "London", "방콕": "Bangkok",
        "싱가포르": "Singapore", "바르셀로나": "Barcelona",
        "로마": "Rome", "암스테르담": "Amsterdam", "프랑크푸르트": "Frankfurt",
    }

    PREF_KEYWORDS = {
        "near_eiffel_tower": ["에펠탑", "에펠 타워", "eiffel"],
        "breakfast_included": ["조식", "아침 포함", "breakfast"],
        "near_metro": ["역세권", "지하철", "metro", "subway"],
        "value_for_money": ["가성비", "합리적", "affordable"],
        "high_review_score": ["높은 평점", "리뷰 좋은", "high rating"],
        "luxury_stay": ["럭셔리", "고급", "5성급", "luxury", "premium"],
    }

    departure_date, return_date = extract_dates(text)
    destination = next((eng for kor, eng in DEST_MAP.items() if kor in text), "")
    adults_match = re.search(r"성인\s*(\d+)명", text)
    adults = int(adults_match.group(1)) if adults_match else 1
    prefs = [tag for tag, kws in PREF_KEYWORDS.items() if any(kw in text for kw in kws)]

    return {
        "origin": extract_origin(text),
        "destination": destination,
        "departureDate": departure_date,
        "returnDate": return_date,
        "adults": adults,
        "hotelPreference": prefs,
    }


def parse_travel_request(text: str) -> dict:
    if OPENAI_API_KEY:
        try:
            result = _parse_with_llm(text)
            result.setdefault("origin", "서울")
            result.setdefault("destination", "")
            result.setdefault("departureDate", "2026-07-10")
            result.setdefault("returnDate", "2026-07-15")
            result.setdefault("adults", 1)
            result.setdefault("hotelPreference", [])
            return result
        except Exception as e:
            print(f"[parser] LLM failed, falling back to regex: {e}")

    return _parse_with_regex(text)


if __name__ == "__main__":
    user_input = "7월 10일부터 7월 15일까지 파리 여행 가고 싶어. 성인 2명이고 에펠탑 근처 호텔이면 좋겠어."
    result = parse_travel_request(user_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))
