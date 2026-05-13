import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
BOOKING_HOST = os.environ.get("BOOKING_RAPIDAPI_HOST", "booking-com15.p.rapidapi.com")


def _headers() -> dict:
    return {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": BOOKING_HOST,
    }


def _get(path: str, params: dict) -> dict:
    url = f"https://{BOOKING_HOST}{path}"
    response = requests.get(url, headers=_headers(), params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def search_destination(city: str) -> str | None:
    """도시명으로 Booking.com dest_id를 반환합니다."""
    data = _get("/api/v1/hotels/searchDestination", {"query": city})
    results = data.get("data", [])
    if not results:
        return None
    return results[0].get("dest_id")


def search_hotels(
    dest_id: str,
    checkin: str,
    checkout: str,
    adults: int = 1,
    currency: str = "KRW",
    language: str = "ko",
    limit: int = 10,
) -> list[dict]:
    """호텔 목록을 검색하고 정규화된 리스트를 반환합니다."""
    params = {
        "dest_id": dest_id,
        "search_type": "CITY",
        "arrival_date": checkin,
        "departure_date": checkout,
        "adults": adults,
        "currency_code": currency,
        "languagecode": language,
        "page_number": 1,
        "units": "metric",
    }
    data = _get("/api/v1/hotels/searchHotels", params)
    hotels_raw = data.get("data", {}).get("hotels", [])
    return [_normalize_hotel(h) for h in hotels_raw[:limit]]


def _normalize_hotel(raw: dict) -> dict:
    prop = raw.get("property", {})
    price_info = prop.get("priceBreakdown", {})
    gross = price_info.get("grossPrice", {})
    price_amount = gross.get("value")
    currency = gross.get("currency", "KRW")

    hotel_id = raw.get("hotel_id") or prop.get("id")
    checkin = prop.get("checkinDate", "")
    checkout = prop.get("checkoutDate", "")

    deep_link = (
        f"https://www.booking.com/searchresults.html"
        f"?dest_id={hotel_id}&dest_type=hotel"
        f"&checkin={checkin}&checkout={checkout}"
    ) if hotel_id else None

    return {
        "hotelId": hotel_id,
        "name": prop.get("name"),
        "reviewScore": prop.get("reviewScore"),
        "reviewScoreWord": prop.get("reviewScoreWord"),
        "reviewCount": prop.get("reviewCount"),
        "stars": prop.get("propertyClass"),
        "price": round(price_amount) if price_amount else None,
        "currency": currency,
        "checkin": checkin,
        "checkout": checkout,
        "latitude": prop.get("latitude"),
        "longitude": prop.get("longitude"),
        "photoUrl": prop.get("photoUrls", [None])[0],
        "deepLink": deep_link,
    }


def get_room_list(
    hotel_id: str | int,
    checkin: str,
    checkout: str,
    adults: int = 1,
    currency: str = "KRW",
    language: str = "ko",
) -> list[dict]:
    """선택한 호텔의 객실 옵션을 반환합니다."""
    params = {
        "hotel_id": hotel_id,
        "arrival_date": checkin,
        "departure_date": checkout,
        "adults": adults,
        "currency_code": currency,
        "languagecode": language,
        "units": "metric",
    }
    data = _get("/api/v1/hotels/getRoomListWithAvailability", params)
    available = data.get("available", [])

    result = []
    for room in available:
        price_breakdown = room.get("product_price_breakdown", {})
        gross = price_breakdown.get("gross_amount_per_night") or price_breakdown.get("gross_amount", {})
        price_value = gross.get("value") if isinstance(gross, dict) else None

        highlights = [h.get("translated_name", "") for h in room.get("bh_room_highlights", []) if h.get("translated_name")]

        result.append({
            "roomId": room.get("room_id"),
            "roomName": room.get("room_name") or room.get("name"),
            "maxOccupancy": room.get("max_occupancy"),
            "price": round(float(price_value)) if price_value else None,
            "currency": currency,
            "breakfastIncluded": bool(room.get("breakfast_included")),
            "freeCancellation": bool(room.get("refundable")),
            "payLater": bool(room.get("choose_when_you_pay")),
            "highlights": highlights,
        })

    return result
