from typing import Optional

from intents import Intent


class IntentClassifier:
    def classify(self, message: str, context: Optional[dict] = None) -> Intent:
        text = message.replace(" ", "").lower()
        has_trip_id = bool(
            context and isinstance(context.get("trip_id"), str) and context.get("trip_id")
        )

        if "cancel" in text or "취소" in text:
            return Intent.CANCEL_PLAN

        strong_modify_tokens = (
            "수정",
            "변경",
            "바꿔",
            "업데이트",
            "짠것중",
            "짜놓",
            "기존일정",
            "기존계획",
            "만들어둔일정",
        )
        if any(token in text for token in strong_modify_tokens):
            return Intent.MODIFY_PLAN

        explicit_modify_tokens = (
            "추가",
            "더넣",
            "넣어줘",
            "하나더",
            "더추가",
            "빼줘",
            "제외",
            "삭제",
            "제거",
            "없애",
            "대신",
            "교체",
            "옮겨",
            "이동",
            "스왑",
            "미술관하루",
            "일차",
            "일째",
            "번째날",
            "첫째날",
            "둘째날",
            "셋째날",
        )
        if any(token in text for token in explicit_modify_tokens):
            return Intent.MODIFY_PLAN

        contextual_modify_tokens = (
            "여유롭게",
            "빡세게",
            "줄여",
            "완화",
            "너무많",
            "과해",
            "도보위주",
            "대중교통위주",
            "환승최소",
            "개만",
        )
        existing_plan_markers = ("짠것중", "짜놓", "기존일정", "기존계획", "만들어둔일정")
        has_day_marker = any(
            token in text for token in ("일차", "일째", "번째날", "첫째날", "둘째날", "셋째날")
        )
        if any(token in text for token in contextual_modify_tokens):
            if has_trip_id or has_day_marker or any(token in text for token in existing_plan_markers):
                return Intent.MODIFY_PLAN

        create_tokens = ("일정", "계획", "코스", "여행", "일정표")
        create_verbs = ("만들", "짜", "추천", "세워", "구성")
        if any(token in text for token in create_tokens) and any(verb in text for verb in create_verbs):
            return Intent.CREATE_PLAN

        return Intent.CREATE_PLAN


default_intent_classifier = IntentClassifier()


def extract_intent(message: str, context: Optional[dict] = None) -> Intent:
    return default_intent_classifier.classify(message, context)
