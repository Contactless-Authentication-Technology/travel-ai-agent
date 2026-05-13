import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
KIWI_HOST = os.environ.get("KIWI_RAPIDAPI_HOST", "kiwi-com-flights-api.p.rapidapi.com")

IATA_MAP: dict[str, str] = {
    "서울": "ICN",
    "인천": "ICN",
    "김포": "GMP",
    "부산": "PUS",
    "제주": "CJU",
    "대구": "TAE",
    "청주": "CJJ",
    "파리": "CDG",
    "paris": "CDG",
    "도쿄": "NRT",
    "tokyo": "NRT",
    "오사카": "KIX",
    "osaka": "KIX",
    "뉴욕": "JFK",
    "new york": "JFK",
    "런던": "LHR",
    "london": "LHR",
    "방콕": "BKK",
    "bangkok": "BKK",
    "싱가포르": "SIN",
    "singapore": "SIN",
    "바르셀로나": "BCN",
    "barcelona": "BCN",
    "로마": "FCO",
    "rome": "FCO",
    "암스테르담": "AMS",
    "amsterdam": "AMS",
    "프랑크푸르트": "FRA",
    "frankfurt": "FRA",
}


def city_to_iata(city: str) -> str | None:
    return IATA_MAP.get(city) or IATA_MAP.get(city.lower())


def _normalize_sector(sector: dict) -> dict:
    segments = sector.get("segments", [])
    if not segments:
        return {}

    first = segments[0]
    last = segments[-1]
    duration_sec = sector.get("duration_seconds", 0)
    carriers = sector.get("carriers", [])

    return {
        "flyFrom": first["source"]["station"]["code"],
        "flyFromCity": first["source"]["station"]["city"],
        "flyTo": last["destination"]["station"]["code"],
        "flyToCity": last["destination"]["station"]["city"],
        "departure": first["source"]["local_time"],
        "arrival": last["destination"]["local_time"],
        "durationHours": round(duration_sec / 3600, 1) if duration_sec else None,
        "stops": len(segments) - 1,
        "airlines": [c["code"] for c in carriers],
        "airlineNames": [c["name"] for c in carriers],
    }


def normalize_flight(itinerary: dict) -> dict:
    price_raw = itinerary.get("price", {}).get("amount")
    price = round(float(price_raw)) if price_raw else None

    outbound = _normalize_sector(itinerary.get("outbound", {}))
    if not outbound:
        return {}

    inbound = _normalize_sector(itinerary.get("inbound", {})) if itinerary.get("inbound") else None

    booking_options = itinerary.get("booking_options", [])
    deep_link = booking_options[0].get("booking_url") if booking_options else None

    result = {
        "id": itinerary.get("id"),
        "price": price,
        "deepLink": deep_link,
        **outbound,
    }

    if inbound:
        result["returnDeparture"] = inbound["departure"]
        result["returnArrival"] = inbound["arrival"]
        result["returnDurationHours"] = inbound["durationHours"]
        result["returnStops"] = inbound["stops"]

    return result


def search_price_calendar(
    fly_from: str,
    fly_to: str,
    month: str,
    adults: int = 1,
    currency: str = "KRW",
) -> dict:
    params = {
        "source": fly_from,
        "destination": fly_to,
        "month": month,
        "adults": adults,
        "currency": currency,
    }

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": KIWI_HOST,
    }

    response = requests.get(
        f"https://{KIWI_HOST}/api/v1/flights/price-calendar",
        headers=headers,
        params=params,
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()
    days = [
        {"date": d["date"], "price": round(float(d["price"]))}
        for d in data.get("days", [])
    ]
    cheapest = data.get("cheapest", {})

    return {
        "month": data.get("month"),
        "currency": data.get("currency"),
        "days": days,
        "cheapestDate": cheapest.get("date") if cheapest else None,
        "cheapestPrice": round(float(cheapest.get("price", 0))) if cheapest else None,
    }


def search_flights(
    fly_from: str,
    fly_to: str,
    departure_date: str,
    return_date: str | None = None,
    adults: int = 1,
    currency: str = "KRW",
    limit: int = 5,
) -> list[dict]:
    params: dict = {
        "source": fly_from,
        "destination": fly_to,
        "departure_date": departure_date,
        "adults": adults,
        "currency": currency,
        "limit": limit,
    }

    if return_date:
        params["return_date"] = return_date

    endpoint = "search-roundtrip" if return_date else "search-oneway"

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": KIWI_HOST,
    }

    response = requests.get(
        f"https://{KIWI_HOST}/api/v1/flights/{endpoint}",
        headers=headers,
        params=params,
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()
    itineraries = data.get("itineraries", [])
    return [f for f in (normalize_flight(i) for i in itineraries) if f]
