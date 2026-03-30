import re
from datetime import date
from typing import Any, Dict, Optional, Tuple

from intents import Intent
from schemas import CreatePlanPayload

FAMILY_TOKENS = (
    "부모님",
    "엄마",
    "아빠",
    "형",
    "누나",
    "동생",
    "사촌",
    "조카",
    "외할아버지",
    "외할머니",
    "친할아버지",
    "친할머니",
    "할머니",
    "할아버지",
    "이모",
    "이모부",
    "고모",
    "고모부",
    "삼촌",
    "숙모",
    "이모할머니",
    "이모할아버지",
)

KOREAN_TOTAL_MAP = {
    "혼자": 1,
    "둘이서": 2,
    "둘이": 2,
    "셋이서": 3,
    "셋이": 3,
    "넷이서": 4,
    "넷이": 4,
    "다섯이서": 5,
    "다섯이": 5,
    "여섯이서": 6,
    "여섯이": 6,
    "일곱이서": 7,
    "일곱이": 7,
    "여덟이서": 8,
    "여덟이": 8,
    "아홉이서": 9,
    "아홉이": 9,
    "열명이서": 10,
    "열이": 10,
}

KOREAN_KNUM_MAP = {
    "한": 1,
    "두": 2,
    "세": 3,
    "네": 4,
    "다섯": 5,
    "여섯": 6,
    "일곱": 7,
    "여덟": 8,
    "아홉": 9,
    "열": 10,
}

ROMANCE_COUPLE_TOKENS = ("커플", "연인", "여자친구", "남자친구", "로맨스", "허니문", "신혼여행")
ROMANCE_THEME_TOKENS = ("로맨스", "허니문", "신혼여행")
FILIAL_THEME_TOKENS = ("효도여행",)
GENERIC_CHILD_TOKENS = ("아이", "아이들", "애", "애들", "아들", "딸", "자녀")
KNOWN_PLACE_TOKENS = ("루브르", "오르세", "에펠탑", "개선문", "몽마르트", "몽마르트르", "노트르담", "베르사유")
LOW_WALK_TOKENS = (
    "걷기는적게",
    "걷기적게",
    "걸음적게",
    "도보적게",
    "많이안걷게",
    "많이걷지않게",
    "걷는거리줄여",
    "걷는거리적게",
    "걷는거리짧게",
)
WALK_MODE_TOKENS = ("도보위주", "걸어서", "걸어다니는", "걸어다닐", "도보로만")
TRANSIT_MODE_TOKENS = ("대중교통위주", "지하철위주", "버스위주", "대중교통으로만")
SLOW_PACE_TOKENS = ("여유롭게", "넉넉하게", "넉넉히", "천천히", "느긋", "쉬엄쉬엄")
FAST_PACE_TOKENS = ("빡세게", "타이트", "빽빽")
THEME_TOKEN_MAP: dict[str, tuple[str, ...]] = {
    "activity": ("액티비티", "액티비티위주", "체험", "체험형", "체험위주", "야외활동", "스포츠", "활동적인", "액티브"),
    "history": ("역사", "역사투어", "역사여행", "역사위주", "유적", "유서깊은", "스토리있는", "역사적인", "유적지"),
    "museum": ("미술관위주", "박물관위주", "전시위주", "미술관투어", "박물관투어", "전시회", "전시관람", "전시보는"),
    "art": ("예술", "예술여행", "아트", "아트투어", "예술감성", "갤러리위주", "갤러리", "전시감상"),
    "architecture": ("건축", "건축투어", "건축물", "건축위주", "건축물구경"),
    "nature": ("자연", "공원위주", "피크닉", "정원", "자연위주", "산책", "강변"),
    "foodie": ("맛집", "맛집투어", "미식", "식도락", "먹방", "음식위주", "디저트", "빵지순례"),
    "cafe": ("카페위주", "카페많이", "브런치투어"),
    "shopping": ("쇼핑위주", "쇼핑많이", "편집샵", "빈티지샵", "아울렛"),
    "night_view": ("야경위주", "야경많이", "밤거리", "야간감성"),
    "healing": ("힐링", "휴양", "쉼위주", "휴식위주"),
    "local": ("로컬", "로컬위주", "현지감성", "골목투어", "동네투어", "현지인", "동네느낌"),
    "hidden_gems": ("숨은명소", "숨겨진명소", "잘안알려진", "비주류명소", "한적한명소", "숨겨진곳"),
    "photo": ("사진위주", "포토스팟", "인생샷", "사진맛집", "사진많이", "사진남기고", "사진잔뜩"),
    "luxury": ("럭셔리", "고급", "프리미엄"),
    "budget": ("가성비", "저렴하게", "알뜰하게", "아껴서"),
    "landmark": ("랜드마크", "명소위주", "대표관광지"),
    "culture": ("문화", "문화예술", "공연", "뮤지컬", "콘서트", "오페라", "연극", "클래식"),
}

_KIN_PREFIX_PATTERN = (
    "부모님|엄마|아빠|형|누나|동생|사촌|조카|"
    "외할아버지|외할머니|친할아버지|친할머니|"
    "할머니|할아버지|이모|이모부|고모|고모부|삼촌|숙모|이모할머니|이모할아버지"
)


def _extract_days(message: str) -> Tuple[Optional[int], Optional[str], Optional[str], str]:
    text = message.replace(" ", "")

    def _calc_range_days(y1: int, m1: int, d1: int, y2: int, m2: int, d2: int) -> Tuple[int, str, str]:
        start = date(y1, m1, d1)
        end = date(y2, m2, d2)
        delta = (end - start).days + 1
        if delta < 1:
            raise ValueError("End date before start date.")
        return delta, start.isoformat(), end.isoformat()

    m = re.search(
        r"(\d{4})년(\d{1,2})월(\d{1,2})일(?:부터|~|-|–|—)?(\d{4})년(\d{1,2})월(\d{1,2})일(?:까지)?",
        text,
    )
    if m:
        try:
            y1, mo1, d1, y2, mo2, d2 = map(int, m.groups())
            days, start_iso, end_iso = _calc_range_days(y1, mo1, d1, y2, mo2, d2)
            return days, start_iso, end_iso, "explicit"
        except ValueError:
            return None, None, None, "missing"

    m = re.search(
        r"(\d{1,2})월(\d{1,2})일(?:부터|~|-|–|—)?(\d{1,2})월(\d{1,2})일(?:까지)?",
        text,
    )
    if m:
        try:
            mo1, d1, mo2, d2 = map(int, m.groups())
            y = date.today().year
            days, start_iso, end_iso = _calc_range_days(y, mo1, d1, y, mo2, d2)
            return days, start_iso, end_iso, "explicit"
        except ValueError:
            return None, None, None, "missing"

    m = re.search(r"(\d{1,2})월(\d{1,2})일(?:부터|~|-|–|—)?(\d{1,2})일(?:까지)?", text)
    if m:
        try:
            mo, d1, d2 = map(int, m.groups())
            y = date.today().year
            days, start_iso, end_iso = _calc_range_days(y, mo, d1, y, mo, d2)
            return days, start_iso, end_iso, "explicit"
        except ValueError:
            return None, None, None, "missing"

    m = re.search(r"(\d+)박(\d+)일", text)
    if m:
        return int(m.group(2)), None, None, "explicit"

    for m in re.finditer(r"(\d+)\s*일", message):
        prefix = message[: m.start()].rstrip()
        if prefix.endswith("월"):
            continue
        return int(m.group(1)), None, None, "explicit"

    return None, None, None, "missing"


def _infer_include_speaker(text: str) -> bool:
    if ("여행가신다고" in text or "여행가시" in text or "가신다고" in text) and "내가" in text and ("계획" in text):
        return False

    if re.search(r"[가-힣]{1,12}(?:이랑|랑|와|과|하고)[가-힣]{1,12}(?:이|가)(?!랑).{0,12}여행(?:가|간|갈)", text):
        return False

    if any(t in text for t in ("내가", "우리", "나랑", "저랑", "제가", "같이", "모시고")):
        return True

    has_trip_request = any(
        t in text
        for t in (
            "여행",
            "일정",
            "계획",
            "코스",
            "일정표",
            "짜줘",
            "세워",
            "구성",
            "다녀오",
            "놀러",
            "가고싶",
            "가고싶어",
            "가볼",
            "갈래",
            "가자",
            "떠나",
            "출발",
        )
    )
    companion_count = len(re.findall(r"(?:이랑|랑|하고|과|와)", text))
    has_family = any(tok in text for tok in FAMILY_TOKENS) or any(tok in text for tok in GENERIC_CHILD_TOKENS)

    if has_trip_request and has_family and companion_count >= 1:
        return True
    return False


def _extract_generic_child_count(text: str) -> int:
    total = 0
    child_pattern = r"(?:아이들|아이|애들|애|아들|딸|자녀)"
    knum = r"(한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)"

    for m in re.finditer(rf"{child_pattern}\s*(\d+)\s*명", text):
        total += int(m.group(1))
    for m in re.finditer(rf"(\d+)\s*명의?\s*{child_pattern}", text):
        total += int(m.group(1))
    for m in re.finditer(rf"{child_pattern}{knum}\s*명", text):
        total += KOREAN_KNUM_MAP[m.group(1)]
    for m in re.finditer(rf"{knum}\s*명의?\s*{child_pattern}", text):
        total += KOREAN_KNUM_MAP[m.group(1)]

    if total > 0:
        return total
    return 1 if any(token in text for token in GENERIC_CHILD_TOKENS) else 0


def _count_family_members(text: str) -> int:
    def _count_for_token(token: str, default_if_present: int = 1) -> int:
        total = 0
        token_pattern = re.escape(token)
        if token == "이모":
            token_pattern = r"이모(?!부|할머니|할아버지)"
        elif token == "고모":
            token_pattern = r"고모(?!부)"
        elif token == "할머니":
            token_pattern = r"(?<!친)(?<!외)(?<!이모)할머니"
        elif token == "할아버지":
            token_pattern = r"(?<!친)(?<!외)(?<!이모)할아버지"

        for m in re.finditer(rf"{token_pattern}\s*(\d+)\s*명", text):
            total += int(m.group(1))
        for m in re.finditer(rf"(\d+)\s*명의?\s*{token_pattern}", text):
            total += int(m.group(1))

        knum = r"(한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)"
        for m in re.finditer(rf"{token_pattern}{knum}\s*명", text):
            total += KOREAN_KNUM_MAP[m.group(1)]
        for m in re.finditer(rf"{knum}\s*명의?\s*{token_pattern}", text):
            total += KOREAN_KNUM_MAP[m.group(1)]

        if total > 0:
            return total
        return default_if_present if re.search(token_pattern, text) else 0

    family_total = 0
    if "부모님" in text:
        family_total += 2
    else:
        family_total += _count_for_token("엄마")
        family_total += _count_for_token("아빠")

    for token in (
        "형",
        "누나",
        "동생",
        "사촌",
        "조카",
        "외할아버지",
        "외할머니",
        "친할아버지",
        "친할머니",
        "할머니",
        "할아버지",
        "이모",
        "이모부",
        "고모",
        "고모부",
        "삼촌",
        "숙모",
        "이모할머니",
        "이모할아버지",
    ):
        family_total += _count_for_token(token)
    return family_total


def _extract_party(message: str) -> Dict[str, Any]:
    text = message.replace(" ", "")
    party: Dict[str, Any] = {
        "adult": 0,
        "highschool": 0,
        "middleschool": 0,
        "elementary": 0,
        "toddler": 0,
        "trip_style": "unknown",
    }

    def _parse_count(token: str) -> int:
        if token.isdigit():
            return int(token)
        return KOREAN_KNUM_MAP[token]

    def _sum_matches(patterns: Tuple[str, ...]) -> int:
        total = 0
        for pattern in patterns:
            for m in re.finditer(pattern, text):
                total += _parse_count(m.group(1))
        return total

    count_token = r"\d+|한|두|세|네|다섯|여섯|일곱|여덟|아홉|열"
    party["highschool"] = _sum_matches((rf"고등학생\s*({count_token})\s*명", rf"({count_token})\s*명의?\s*고등학생"))
    party["middleschool"] = _sum_matches((rf"중학생\s*({count_token})\s*명", rf"({count_token})\s*명의?\s*중학생"))
    party["elementary"] = _sum_matches((rf"초등학생\s*({count_token})\s*명", rf"({count_token})\s*명의?\s*초등학생"))
    party["toddler"] = _sum_matches((rf"(?:애기|아기|유아|영아)\s*({count_token})\s*명", rf"({count_token})\s*명의?\s*(?:애기|아기|유아|영아)"))
    party["adult"] = _sum_matches((rf"성인\s*({count_token})\s*명", rf"({count_token})\s*명의?\s*성인"))
    generic_child_count = _extract_generic_child_count(text)
    if generic_child_count > 0 and (party["highschool"] + party["middleschool"] + party["elementary"] + party["toddler"]) == 0:
        party["elementary"] = generic_child_count

    family_members = _count_family_members(text)

    age_kin_map = [
        ("highschool", ("고등학생", "고딩"), ("동생", "형", "누나", "사촌", "조카")),
        ("middleschool", ("중학생", "중딩"), ("동생", "형", "누나", "사촌", "조카")),
        ("elementary", ("초등학생", "초딩"), ("동생", "형", "누나", "사촌", "조카")),
        ("toddler", ("애기", "아기", "유아", "영아"), ("동생", "조카")),
    ]
    knum_pattern = r"(한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)"
    for bucket, age_terms, kin_terms in age_kin_map:
        matched = False
        for age_term in age_terms:
            for kin_term in kin_terms:
                base = f"{age_term}{kin_term}"
                n: Optional[int] = None
                m_digit = re.search(rf"{base}(\d+)\s*명", text)
                if m_digit:
                    n = int(m_digit.group(1))
                else:
                    m_knum = re.search(rf"{base}{knum_pattern}\s*명", text)
                    if m_knum:
                        n = KOREAN_KNUM_MAP[m_knum.group(1)]

                if base in text:
                    party[bucket] = max(int(party[bucket]), n or 1)
                    dec = n or 1
                    family_members = max(0, family_members - dec)
                    matched = True
                    break
            if matched:
                break

    if int(party["adult"]) == 0 and family_members > 0:
        party["adult"] = family_members

    parsed_sum = int(party["adult"]) + int(party["highschool"]) + int(party["middleschool"]) + int(party["elementary"]) + int(party["toddler"])
    total_people: Optional[int] = None

    m = re.search(r"총\s*(\d+)\s*명", text)
    if m:
        total_people = int(m.group(1))

    if total_people is None:
        for k, v in KOREAN_TOTAL_MAP.items():
            if k in text:
                total_people = v
                break

    if total_people is None:
        m = re.search(r"(한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*명(?:이서|에서|과|이)?", text)
        if m and not re.search(rf"(?:{_KIN_PREFIX_PATTERN}){m.group(1)}\s*명", text):
            total_people = KOREAN_KNUM_MAP[m.group(1)]

    if total_people is None and parsed_sum == 0:
        m = re.search(r"(\d+)\s*명(?:이서|에서|과|이)?", text)
        if m:
            total_people = int(m.group(1))

    if total_people is not None and parsed_sum < total_people:
        party["adult"] += total_people - parsed_sum

    include_speaker = _infer_include_speaker(text)
    if include_speaker and family_members > 0 and total_people is None:
        party["adult"] += 1

    if "혼자" in message or "솔로" in message:
        party["trip_style"] = "solo"
    elif any(tok in message for tok in ROMANCE_COUPLE_TOKENS):
        party["trip_style"] = "couple"
    elif "친구" in message:
        party["trip_style"] = "friends"
    elif (
        any(tok in message for tok in FAMILY_TOKENS)
        or ("가족" in message)
        or any(tok in message for tok in FILIAL_THEME_TOKENS)
        or generic_child_count > 0
    ):
        party["trip_style"] = "family"

    if party["trip_style"] == "couple" and total_people is None:
        party["adult"] = max(int(party["adult"]), 2)

    if int(party["adult"]) <= 0:
        party["adult"] = 1
    return party


def _extract_walk_limit(message: str) -> Optional[int]:
    text = message.lower().replace(" ", "")
    m = re.search(r"(?:하루)?(\d+)\s*km(?:까지)?(?:이하|이내)", text)
    if m:
        return int(m.group(1))
    return None


def _extract_museum_limit(message: str) -> Optional[int]:
    text = message.replace(" ", "")
    m = re.search(r"(?:박물관|미술관)(?:은)?하루(\d+)개만", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:박물관|미술관)(?:은)?하루(한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)개만", text)
    if m:
        return KOREAN_KNUM_MAP[m.group(1)]
    return None


def _extract_place_preferences(message: str) -> Tuple[list[str], list[str]]:
    text = message.replace(" ", "")
    must_include: list[str] = []
    must_avoid: list[str] = []

    for place in KNOWN_PLACE_TOKENS:
        if re.search(rf"{place}(?:은|는|이|가)?(?:꼭|반드시|무조건)", text) or re.search(
            rf"{place}.{{0,10}}(?:넣고싶|넣어줘|포함|가고싶|꼭가고싶|꼭보고싶)", text
        ):
            must_include.append(place)
        if re.search(rf"{place}(?:은|는|이|가)?(?:빼줘|빼고|제외|싫어|피하고싶|안가고싶|빼고싶)", text):
            must_avoid.append(place)

    return list(dict.fromkeys(must_include)), list(dict.fromkeys(must_avoid))


def _extract_themes(message: str) -> list[str]:
    compact = message.replace(" ", "")
    themes: list[str] = []

    for theme, tokens in THEME_TOKEN_MAP.items():
        if any(token in compact for token in tokens):
            themes.append(theme)

    return list(dict.fromkeys(themes))


def _apply_rule_overrides(plan: CreatePlanPayload, message: str) -> CreatePlanPayload:
    plan.intent = Intent.CREATE_PLAN.value
    plan.destination.city = "Paris"
    plan.destination.country = "FR"
    compact = message.replace(" ", "")

    days, start_iso, end_iso, source = _extract_days(message)
    plan.dates.days = (max(1, days) if isinstance(days, int) else None)
    plan.dates.source = source
    plan.dates.start_date = start_iso
    plan.dates.end_date = end_iso

    p = _extract_party(message)
    plan.party.adult = int(p.get("adult", 0))
    plan.party.highschool = int(p.get("highschool", 0))
    plan.party.middleschool = int(p.get("middleschool", 0))
    plan.party.elementary = int(p.get("elementary", 0))
    plan.party.toddler = int(p.get("toddler", 0))
    plan.party.trip_style = str(p.get("trip_style", "unknown"))

    if any(token in compact for token in WALK_MODE_TOKENS):
        plan.mobility.travel_mode = "walk"
    elif any(token in compact for token in TRANSIT_MODE_TOKENS):
        plan.mobility.travel_mode = "transit"
    else:
        plan.mobility.travel_mode = "both"

    if re.search(r"환승(?:은)?(?:최소|적게|줄여)", compact):
        plan.mobility.optimize = "min_transfers"

    walk_limit = _extract_walk_limit(message)
    if walk_limit is not None:
        plan.mobility.max_walk_km_per_day = walk_limit
    elif any(token in compact for token in LOW_WALK_TOKENS):
        plan.mobility.max_walk_km_per_day = 5

    if any(token in compact for token in LOW_WALK_TOKENS) and plan.mobility.travel_mode == "both":
        plan.mobility.travel_mode = "transit"

    if "휠체어" in compact:
        plan.mobility.wheelchair = True

    if "유모차" in compact:
        plan.mobility.stroller = True

    if any(token in message for token in SLOW_PACE_TOKENS):
        plan.pace.level = "slow"
    elif any(token in message for token in FAST_PACE_TOKENS):
        plan.pace.level = "fast"

    if any(tok in message for tok in ROMANCE_THEME_TOKENS) and "romance" not in plan.preferences.themes:
        plan.preferences.themes.append("romance")
    if any(tok in message for tok in FILIAL_THEME_TOKENS) and "family" not in plan.preferences.themes:
        plan.preferences.themes.append("family")
    if "가족여행" in compact and "family" not in plan.preferences.themes:
        plan.preferences.themes.append("family")
    for theme in _extract_themes(message):
        if theme not in plan.preferences.themes:
            plan.preferences.themes.append(theme)

    if "cafe" in plan.preferences.themes:
        plan.preferences.weights.cafe = 0.8
        plan.preferences.weights.museum = 0.3

    if "shopping" in plan.preferences.themes:
        plan.preferences.weights.shopping = 0.8

    if "night_view" in plan.preferences.themes:
        plan.preferences.weights.night_view = 0.8

    if "nature" in plan.preferences.themes:
        plan.preferences.weights.park = 0.8

    if "museum" in plan.preferences.themes:
        plan.preferences.weights.museum = max(plan.preferences.weights.museum, 0.85)

    if "art" in plan.preferences.themes:
        plan.preferences.weights.museum = max(plan.preferences.weights.museum, 0.75)

    if "luxury" in plan.preferences.themes:
        plan.budget.budget_mode = "flex"

    if "budget" in plan.preferences.themes:
        plan.budget.budget_mode = "save"

    if any(token in compact for token in ("실내위주", "실내로만", "실내만")):
        plan.constraints.indoor_focus = True

    if any(token in compact for token in ("비오면", "비올때", "비올때는", "우천", "우천시")):
        plan.constraints.rainy_plan = True

    museum_limit = _extract_museum_limit(message)
    if museum_limit is not None:
        plan.constraints.museum_per_day = museum_limit

    must_include, must_avoid = _extract_place_preferences(message)
    if must_include:
        plan.preferences.must_include = must_include
    if must_avoid:
        plan.preferences.must_avoid = must_avoid

    missing = []
    if plan.dates.days is None or plan.dates.source == "missing":
        missing.append("dates.days")
    plan.clarify.missing_fields = missing
    plan.clarify.needed = len(missing) > 0

    return plan
