# parsers/modify_plan/rules.py
import re
from typing import Any, Dict, Optional, List, Tuple

from intents import Intent
from schemas import ModifyPlanPayload, Operation

# 한글 숫자 매핑(개수/인원 등)
KOREAN_KNUM_MAP: Dict[str, int] = {
    "한": 1,
    "하나": 1,
    "두": 2,
    "둘": 2,
    "세": 3,
    "셋": 3,
    "네": 4,
    "넷": 4,
    "다섯": 5,
    "여섯": 6,
    "일곱": 7,
    "여덟": 8,
    "아홉": 9,
    "열": 10,
}

QUANTITY_TOKEN_PATTERN = r"\d+|하나|한|둘|두|셋|세|넷|네|다섯|여섯|일곱|여덟|아홉|열"
LOW_WALK_TOKENS = (
    "걷기는적게",
    "걷기적게",
    "걸음적게",
    "도보적게",
    "많이안걷게",
    "많이걷지않게",
    "걷는거리줄여",
    "걷는거리적게",
)
SLOT_TOKEN_PAIRS = ("오전", "점심", "오후", "저녁", "밤", "야간", "새벽")
INDOOR_TOKENS = ("실내위주", "실내로만", "실내만")
RAINY_TOKENS = ("비오면", "비올때", "우천", "우천시")
WALK_MODE_TOKENS = ("도보위주", "도보로만", "걸어서", "걸어다니는")
TRANSIT_MODE_TOKENS = ("대중교통위주", "지하철위주", "버스위주", "대중교통으로만")
SLOW_PACE_TOKENS = ("여유롭게", "넉넉하게", "넉넉히", "천천히", "느긋", "쉬엄쉬엄")
FAST_PACE_TOKENS = ("빡세게", "더빡세", "빽빽", "더많이")

# MVP: 알려진 장소(추후 DB/NER로 확장)
KNOWN_PLACES: Tuple[str, ...] = (
    "루브르",
    "오르세",
    "에펠탑",
    "개선문",
    "몽마르트",
    "몽마르트르",
    "노트르담",
    "베르사유",
)


# -------------------------
# Target day extraction
# -------------------------
def _extract_target_day(text: str) -> Optional[int]:
    """
    지원:
    - 2일차 / 2일 차
    - 2일째
    - 2번째 날
    - 첫째날/둘째날/셋째날...
    """
    m = re.search(r"(\d+)\s*일\s*차", text)
    if m:
        return int(m.group(1))

    m = re.search(r"(\d+)\s*일\s*째", text)
    if m:
        return int(m.group(1))

    m = re.search(r"(\d+)\s*번째\s*날", text)
    if m:
        return int(m.group(1))

    ordinal_map = {
        "첫째날": 1,
        "둘째날": 2,
        "셋째날": 3,
        "넷째날": 4,
        "다섯째날": 5,
    }
    for token, day in ordinal_map.items():
        if token in text:
            return day

    return None


# -------------------------
# Operation inference
# -------------------------
def _infer_op(text: str) -> str:
    """
    op 우선순위:
    - swap (오전/오후 교체)
    - set_quantity / set_constraint / set_mobility / set_pace
    - add / remove / replace / move
    """
    slot_count = sum(1 for token in SLOT_TOKEN_PAIRS if token in text)
    if slot_count >= 2 and any(t in text for t in ("바꿔", "교체", "스왑")):
        return "swap"

    if re.search(
        rf"({QUANTITY_TOKEN_PATTERN})\s*개(?:를|에서)?\s*"
        rf"({QUANTITY_TOKEN_PATTERN})\s*개(?:로)?",
        text,
    ):
        return "set_quantity"

    if "개" in text and any(token in text for token in ("줄여줘", "늘려줘", "줄여", "늘려")):
        return "set_quantity"

    if ("미술관하루" in text or "박물관하루" in text) and "개만" in text:
        return "set_constraint"

    if any(token in text for token in INDOOR_TOKENS + RAINY_TOKENS):
        return "set_constraint"

    if (
        any(token in text for token in WALK_MODE_TOKENS + TRANSIT_MODE_TOKENS + ("환승최소", "환승적게", "휠체어", "유모차"))
        or re.search(r"환승(?:은)?(?:최소|적게|줄여)", text)
        or any(token in text for token in LOW_WALK_TOKENS)
        or re.search(r"걷는거리.*(?:줄여|줄이고|줄여줘)", text)
        or re.search(r"(?:하루)?\d+\s*km(?:까지)?(?:이하|이내)", text)
    ):
        return "set_mobility"

    # pace (확장)
    if any(token in text for token in FAST_PACE_TOKENS) or ("타이트" in text and not any(token in text for token in ("너무타이트", "타이트해서"))):
        return "set_pace"
    if any(token in text for token in SLOW_PACE_TOKENS):
        return "set_pace"
    if any(token in text for token in ("힘들", "부담", "줄여", "완화", "너무많", "과해", "너무빡세", "빡세서")):
        return "set_pace"

    if any(token in text for token in ("추가", "추가해", "더넣", "하나더", "더넣어")):
        return "add"

    if any(token in text for token in ("빼줘", "제외", "삭제","제거")):
        return "remove"

    if any(token in text for token in ("대신", "바꿔", "교체")):
        return "replace"

    if any(token in text for token in ("옮겨", "이동")):
        return "move"

    return "replace"


def _infer_category(text: str) -> Optional[str]:
    if "카페" in text:
        return "cafe"
    if "박물관" in text or "미술관" in text:
        return "museum"
    if "야경" in text:
        return "night_view"
    if "공원" in text:
        return "park"
    if "쇼핑" in text:
        return "shopping"
    if "맛집" in text or "식당" in text:
        return "restaurant"
    return None


# -------------------------
# Place extraction (개선 버전)
# -------------------------
def _find_place_mentions(message: str) -> List[str]:
    """
    문장에 등장한 장소명을 모두 반환(중복 제거, 등장 순서 유지).
    """
    found: List[str] = []
    for p in KNOWN_PLACES:
        if p in message:
            found.append(p)
    return list(dict.fromkeys(found)) #리스트(또는 반복 가능한 값들)를 받아서 그 값들을 key로 하는 딕셔너리를 만들어주는 함수


def _infer_place_change(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    replace 케이스를 위해 from_place / to_place를 추정한다.
    지원 패턴:
    - "A 대신 B"
    - "A 말고 B"
    - "A -> B", "A→B"
    - "A을/를 B로 바꿔/교체/변경"
    """
    msg = message.replace(" ", "")

    # A대신B / A말고B
    m = re.search(r"(.+?)(?:대신|말고)(.+)", msg)
    if m:
        left, right = m.group(1), m.group(2)
        from_candidates = [p for p in KNOWN_PLACES if p in left] #리스트 컴프리헨션
        to_candidates = [p for p in KNOWN_PLACES if p in right]
        return (from_candidates[0] if from_candidates else None,
                to_candidates[0] if to_candidates else None)

    # A->B / A→B
    m = re.search(r"(.+?)(?:->|→)(.+)", msg)
    if m:
        left, right = m.group(1), m.group(2)
        from_candidates = [p for p in KNOWN_PLACES if p in left]
        to_candidates = [p for p in KNOWN_PLACES if p in right]
        return (from_candidates[0] if from_candidates else None,
                to_candidates[0] if to_candidates else None)

    # A를 B로 바꿔/교체/변경
    m = re.search(r"(.+?)(?:을|를)(.+?)(?:로)(?:바꿔|교체|변경)", msg)
    if m:
        left, right = m.group(1), m.group(2)
        from_candidates = [p for p in KNOWN_PLACES if p in left]
        to_candidates = [p for p in KNOWN_PLACES if p in right]
        return (from_candidates[0] if from_candidates else None,
                to_candidates[0] if to_candidates else None)

    # A에서 B로
    m = re.search(r"(.+?)에서(.+?)로(?:바꿔|교체|변경)?", msg)
    if m:
        left, right = m.group(1), m.group(2)
        from_candidates = [p for p in KNOWN_PLACES if p in left]
        to_candidates = [p for p in KNOWN_PLACES if p in right]
        return (from_candidates[0] if from_candidates else None,
                to_candidates[0] if to_candidates else None)

    # A 빼고 B 넣어줘
    m = re.search(r"(.+?)빼고(.+?)(?:넣어|추가)", msg)
    if m:
        left, right = m.group(1), m.group(2)
        from_candidates = [p for p in KNOWN_PLACES if p in left]
        to_candidates = [p for p in KNOWN_PLACES if p in right]
        return (from_candidates[0] if from_candidates else None,
                to_candidates[0] if to_candidates else None)

    return None, None


def _infer_place_name(message: str, op: str) -> Optional[str]:
    """
    스키마가 place_name 1개만 받으므로:
    - replace면 from_place 우선 반환
    - 그 외는 문장에 등장한 첫 장소명 반환
    """
    mentions = _find_place_mentions(message)

    if op == "replace":
        from_place, _to_place = _infer_place_change(message)
        if from_place:
            return from_place
        # replace인데 패턴이 약하면 첫 mention을 from_place로 사용
        return mentions[0] if mentions else None

    return mentions[0] if mentions else None


def _infer_replace_targets(message: str, category: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    replace 의도를 더 명확히 전달하기 위한 보조 메타 생성.
    - place -> place: from_place / to_place
    - place -> category: from_place / to_category
    """
    if not any(token in message for token in ("대신", "말고", "->", "→", "바꿔", "교체", "변경", "빼고")):
        return None

    from_place, to_place = _infer_place_change(message)
    if from_place and to_place:
        return {
            "replace_mode": "place_to_place",
            "from_place": from_place,
            "to_place": to_place,
        }
    if from_place and category:
        return {
            "replace_mode": "place_to_category",
            "from_place": from_place,
            "to_category": category,
        }
    return None


# -------------------------
# Quantity / Slot
# -------------------------
def _infer_quantity(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*개(?:만|더)?", text)
    if m:
        return int(m.group(1))

    m = re.search(r"(하나|한|둘|두|셋|세|넷|네|다섯|여섯|일곱|여덟|아홉|열)\s*개(?:만|더)?", text)
    if m:
        return KOREAN_KNUM_MAP[m.group(1)]

    m = re.search(r"(하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열)(?:개)?\s*(?:추가|더넣|더넣어|넣어줘)", text)
    if m:
        return KOREAN_KNUM_MAP[m.group(1)]

    if "하나더" in text or "하나 더" in text:
        return 1

    return None


def _infer_quantity_change(text: str) -> tuple[Optional[int], Optional[int]]:
    m = re.search(
        rf"({QUANTITY_TOKEN_PATTERN})\s*개(?:를|에서)?\s*"
        rf"({QUANTITY_TOKEN_PATTERN})\s*개(?:로)?",
        text,
    )
    if not m:
        return None, None

    def parse_num(token: str) -> int:
        if token.isdigit():
            return int(token)
        return KOREAN_KNUM_MAP[token]

    return parse_num(m.group(1)), parse_num(m.group(2))


def _infer_target_slot(text: str) -> Optional[str]:
    slots = _extract_slots_in_order(text)
    return slots[0] if slots else None


def _extract_slots_in_order(text: str) -> List[str]:
    candidates = []
    slot_patterns = (
        ("오전", "morning"),
        ("점심", "lunch"),
        ("오후", "afternoon"),
        ("저녁", "dinner"),
        ("밤", "night"),
        ("야간", "night"),
        ("새벽", "night"),
    )

    for token, slot in slot_patterns:
        index = text.find(token)
        if index >= 0:
            candidates.append((index, slot))

    ordered_slots: List[str] = []
    for _, slot in sorted(candidates, key=lambda item: item[0]):
        if slot not in ordered_slots:
            ordered_slots.append(slot)
    return ordered_slots


def _extract_walk_limit(text: str) -> Optional[int]:
    m = re.search(r"(?:하루)?(\d+)\s*km(?:까지)?(?:이하|이내)", text)
    if m:
        return int(m.group(1))
    return None


def _extract_museum_limit(text: str) -> Optional[int]:
    m = re.search(r"(?:박물관|미술관)(?:은)?하루(\d+)개만", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:박물관|미술관)(?:은)?하루(한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)개만", text)
    if m:
        return KOREAN_KNUM_MAP[m.group(1)]
    return None


def _extract_constraint_patch(text: str) -> Optional[Dict[str, Any]]:
    patch: Dict[str, Any] = {}
    if any(token in text for token in INDOOR_TOKENS):
        patch["indoor_focus"] = True
    if any(token in text for token in RAINY_TOKENS):
        patch["rainy_plan"] = True

    museum_limit = _extract_museum_limit(text)
    if museum_limit is not None:
        patch["museum_per_day"] = museum_limit

    return patch or None


def _extract_mobility_patch(text: str) -> Optional[Dict[str, Any]]:
    mobility: Dict[str, Any] = {}

    if any(token in text for token in WALK_MODE_TOKENS):
        mobility["travel_mode"] = "walk"
    elif any(token in text for token in TRANSIT_MODE_TOKENS):
        mobility["travel_mode"] = "transit"

    if "환승최소" in text or "환승적게" in text or re.search(r"환승(?:은)?(?:최소|적게|줄여)", text):
        mobility["optimize"] = "min_transfers"

    walk_limit = _extract_walk_limit(text)
    if walk_limit is not None:
        mobility["max_walk_km_per_day"] = walk_limit
    elif any(token in text for token in LOW_WALK_TOKENS) or re.search(r"걷는거리.*(?:줄여|줄이고|줄여줘)", text):
        mobility["max_walk_km_per_day"] = 5
        mobility.setdefault("travel_mode", "transit")

    if "휠체어" in text:
        mobility["wheelchair"] = True

    if "유모차" in text:
        mobility["stroller"] = True

    return mobility or None


# -------------------------
# Build operation (rules)
# -------------------------
def _build_operation(message: str) -> Operation:
    text = message.replace(" ", "")

    op = _infer_op(text)
    day = _extract_target_day(text)
    category = _infer_category(text)
    quantity = _infer_quantity(text)
    from_quantity, to_quantity = _infer_quantity_change(text)
    target_slot = _infer_target_slot(text)
    swap_slots: Optional[List[str]] = None
    ordered_slots = _extract_slots_in_order(text)

    # place_name (개선된 추출 적용)
    place_name = _infer_place_name(message, op)

    # constraint patch
    constraints_patch: Optional[Dict[str, Any]] = None
    if op == "set_quantity":
        quantity = None
    elif op == "replace":
        quantity = None

    if op == "set_constraint":
        constraints_patch = _extract_constraint_patch(text)

    if ("미술관하루" in text or "박물관하루" in text) and "개만" in text:
        if constraints_patch is None:
            constraints_patch = {}
        m = re.search(r"(?:미술관|박물관)하루\s*(\d+)\s*개만", text)
        if m:
            constraints_patch["museum_per_day"] = int(m.group(1))
        elif quantity is not None:
            constraints_patch["museum_per_day"] = quantity
        else:
            constraints_patch["museum_per_day"] = 1
        op = "set_constraint"

    # replace 대상(장소->장소 / 장소->카테고리) 메타 보강
    if op == "replace":
        replace_patch = _infer_replace_targets(message, category)
        if replace_patch:
            constraints_patch = {**(constraints_patch or {}), **replace_patch} #constraints_patch와 replace_patch를 합치는 함수

    # swap은 단일 target_slot이 아니라 swap_slots(두 슬롯 교체)로 표현
    if op == "swap":
        slots: List[str] = list(ordered_slots)
        if len(slots) >= 2:
            swap_slots = slots[:2]
        target_slot = None

    # mobility patch
    mobility: Optional[Dict[str, Any]] = _extract_mobility_patch(text)
    if mobility is not None:
        op = "set_mobility" if op not in {"swap", "move", "set_quantity", "set_constraint"} else op

    if op == "move" and len(ordered_slots) >= 2:
        constraints_patch = {**(constraints_patch or {}), "from_slot": ordered_slots[0], "to_slot": ordered_slots[1]}
        target_slot = ordered_slots[1]

    # pace patch (확장)
    pace: Optional[str] = None
    if op not in {"set_quantity", "set_constraint", "set_mobility"}:
        if any(token in text for token in SLOW_PACE_TOKENS) or any(
            token in text for token in ("줄여", "완화", "힘들", "부담", "너무많", "과해", "너무빡세", "빡세서", "너무타이트", "타이트해서")
        ):
            pace = "slow"
            op = "set_pace"
        elif any(token in text for token in FAST_PACE_TOKENS) or ("타이트" in text and not any(token in text for token in ("너무타이트", "타이트해서"))):
            pace = "fast"
            op = "set_pace"

    return Operation(
        op=op,
        target_day=day,
        target_slot=target_slot,
        swap_slots=swap_slots,
        category=category,
        place_name=place_name,
        quantity=quantity,
        from_quantity=from_quantity if op == "set_quantity" else None,
        to_quantity=to_quantity if op == "set_quantity" else None,
        constraints_patch=constraints_patch,
        pace=pace,
        mobility=mobility,
    )


# -------------------------
# Apply rules to payload
# -------------------------
def _apply_rule_overrides(
    payload: ModifyPlanPayload,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> ModifyPlanPayload:
    payload.intent = Intent.MODIFY_PLAN.value

    # trip_id 보완 (context 우선)
    if (not payload.trip_id) and context and isinstance(context.get("trip_id"), str):
        payload.trip_id = context["trip_id"]

    inferred = _build_operation(message)

    if not payload.operations:
        payload.operations = [inferred]
    else:
        # 모든 operation에 규칙 보정 병합 (비어있는 필드만 채움)
        for op in payload.operations:
            if op.target_day is None:
                op.target_day = inferred.target_day
            if op.target_slot is None and op.op != "swap":
                op.target_slot = inferred.target_slot
            if op.swap_slots is None and op.op == "swap":
                op.swap_slots = inferred.swap_slots
            if op.category is None:
                op.category = inferred.category
            if op.place_name is None:
                op.place_name = inferred.place_name
            if op.quantity is None:
                op.quantity = inferred.quantity
            if op.from_quantity is None:
                op.from_quantity = inferred.from_quantity
            if op.to_quantity is None:
                op.to_quantity = inferred.to_quantity
            if op.constraints_patch is None:
                op.constraints_patch = inferred.constraints_patch
            if op.pace is None:
                op.pace = inferred.pace
            if op.mobility is None:
                op.mobility = inferred.mobility

    # missing_fields 정책(MVP)
    missing_fields: List[str] = []

    if not payload.trip_id:
        missing_fields.append("trip_id")
    elif not payload.operations:
        missing_fields.append("operations")
    else:
        def needs_target_day(op: Operation) -> bool:
            if op.op in {"add", "swap", "move"}:
                return op.target_day is None
            if op.op == "set_quantity":
                return op.target_day is None and not op.category and not op.place_name
            if op.op in {"remove", "replace"}:
                return op.target_day is None and not op.place_name
            return False

        if any(needs_target_day(op) for op in payload.operations):
            missing_fields.append("operations.target_day")

    payload.clarify.missing_fields = list(dict.fromkeys(missing_fields))
    payload.clarify.needed = len(payload.clarify.missing_fields) > 0
    return payload
