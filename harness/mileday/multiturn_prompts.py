from __future__ import annotations

import json
from datetime import date

from harness.mileday.dataset import MileDayMultiTurnCase
from harness.mileday.time_prefix import canonical_title_prefix, date_day_of_week, ko_weekday


ACTIVE_MULTITURN_PROMPT_VERSION = "v11"
MILEDAY_MULTITURN_REFERENCE_TIMEZONE = "Asia/Seoul"

PROMPT_VERSION_HISTORY = {
    "v1": "모델이 설명문과 DB payload JSON을 모두 직접 생성하도록 한 초기 버전.",
    "v2": "필수 top-level key, create/partial_update 규칙, confirmation 조건을 강화한 버전.",
    "v3": "deterministic validator 기준에 맞춰 create 최소 milestone과 날짜 검증을 조정한 버전.",
    "v4": "모델이 날짜를 직접 계산하지 않고 harness가 제공한 allowed slot을 쓰도록 한 버전.",
    "v5": "오늘 날짜와 요일 정보를 prompt에 함께 제공해 상대 날짜 혼선을 줄인 버전.",
    "v6": "기존 제약은 유지하되 prompt 길이를 줄이고 judge 재시도 정책을 붙인 버전.",
    "v7": "모델은 slot_id 기반 schedule_plan만 만들고 DB payload는 rule-based로 생성하게 한 버전.",
    "v8": "모델에게 JSON 생성을 요구하지 않고 USER_MESSAGE와 PLAN 블록만 생성하게 한 버전.",
    "v9": "create는 PLAN 전체, partial_update는 PATCH 변경분만 생성하고 병합은 rule-based로 처리하는 버전.",
    "v10": "모델 출력에서 USER_MESSAGE를 제거하고 사용자 설명문도 rule-based로 생성하는 버전.",
    "v11": "모델은 내부 식별자를 생성하지 않고 한글 일정 의도와 작업 후보만 작성하며, slot 매핑과 DB payload는 rule-based로 처리하는 버전.",
}

def build_mileday_multiturn_prompt(
    case: MileDayMultiTurnCase,
    turn_id: int,
    transcript: list[dict[str, str]],
) -> str:
    """Build the active v11 prompt for MileDay multiturn schedule evaluation."""

    turn = case.turns[turn_id - 1]
    allowed_slots = mileday_multiturn_allowed_slots(case)
    reference_date_context = mileday_multiturn_reference_date_context()
    return (
        "당신은 MileDay 일정 제안 도우미입니다.\n"
        "저장용 구조 데이터, 내부 식별자, 날짜 계산, 사용자 설명문을 만들지 마세요.\n"
        "사용자 요청을 일정 의도와 작업 후보로만 정리하세요.\n\n"
        "[출력 형식]\n"
        "[일정_의도]\n"
        "행동: 생성 또는 부분수정\n"
        "대상: 변경 대상 또는 생성 대상\n"
        "변경: 반영할 변경 내용\n"
        "작업:\n"
        "- 작업명\n"
        "- 작업명\n"
        "[/일정_의도]\n\n"
        "[규칙]\n"
        "- 출력에는 [일정_의도], [/일정_의도]만 사용합니다.\n"
        "- 사용자 설명, 구조 데이터, 코드 블록, 표는 쓰지 않습니다.\n"
        "- 내부 식별자, 날짜, 제목 앞 시간표현을 쓰지 않습니다.\n"
        "- 작업명에는 요일/시간 prefix를 넣지 않습니다. 예: '[월 19:00-21:00]' 금지.\n"
        "- 작업명은 한국어로만 작성합니다. 영어 표현을 쓰지 않습니다.\n"
        "- 작업명에는 오전/오후, 날짜, 시간대를 쓰지 않습니다.\n"
        "- 생성 요청의 작업은 준비 흐름이 드러나도록 구체적으로 작성합니다.\n"
        "- 부분수정 요청의 작업은 변경 후 작업명 후보만 작성합니다.\n"
        "- 유지할 항목은 작업 목록에 다시 쓰지 않습니다.\n"
        "- 날짜/요일/시간 배정과 DB 반영은 평가 스크립트가 처리합니다.\n\n"
        "[평가_조건]\n"
        f"- 예상_행동: {_ko_expected_action(turn.expected_action)}\n"
        "- 생성_최소_작업수: 3\n"
        f"- 최대_작업수: {case.expected.constraints.max_milestones}\n"
        f"- 가장_늦은_날짜: {case.expected.constraints.latest_allowed_date}\n\n"
        "[기준_날짜]\n"
        f"{json.dumps(_ko_reference_date_context(reference_date_context), ensure_ascii=False, sort_keys=True)}\n\n"
        "[목표]\n"
        f"{json.dumps(_ko_goal_context(case), ensure_ascii=False, sort_keys=True)}\n\n"
        "[가능_시간]\n"
        f"{json.dumps(_ko_availability_context(case), ensure_ascii=False, sort_keys=True)}\n\n"
        "[배정_가능_후보]\n"
        f"{json.dumps(_ko_allowed_slot_context(allowed_slots), ensure_ascii=False, sort_keys=True)}\n\n"
        "[기존_일정]\n"
        f"{json.dumps(_ko_existing_schedule_context(case), ensure_ascii=False, sort_keys=True)}\n\n"
        "[이전_대화]\n"
        f"{mileday_multiturn_transcript_text(transcript)}\n\n"
        "[사용자_요청]\n"
        f"{turn.content}\n"
    )


def mileday_multiturn_transcript_text(transcript: list[dict[str, str]]) -> str:
    if not transcript:
        return "이전 대화 없음."
    chunks = []
    for index, message in enumerate(transcript, start=1):
        role = message["role"]
        content = message["content"].strip()
        chunks.append(f"{index}. {role}:\n{content}")
    return "\n\n".join(chunks)


def _ko_expected_action(action: str) -> str:
    return {
        "create": "생성",
        "partial_update": "부분수정",
    }.get(action, action)


def _ko_reference_date_context(context: dict[str, str]) -> dict[str, str]:
    return {
        "오늘": context["today"],
        "요일": context["weekday"],
        "시간대": "한국 표준시",
    }


def _ko_goal_context(case: MileDayMultiTurnCase) -> dict[str, str | bool | None]:
    goal = case.input.initial_goal
    return {
        "제목": goal.title,
        "마감일": goal.deadline,
        "반복여부": "예" if goal.is_recurring else "아니오",
        "반복유형": goal.recurrence_type or "",
        "색상": goal.color,
    }


def _ko_availability_context(case: MileDayMultiTurnCase) -> list[dict[str, str]]:
    return [
        {
            "요일": ko_weekday(item.day_of_week),
            "시작": item.start_time,
            "종료": item.end_time,
        }
        for item in case.input.availability
    ]


def _ko_allowed_slot_context(slots: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "순번": str(index),
            "날짜": slot["scheduled_date"],
            "요일": slot["weekday"],
            "시간": slot["time_range"],
        }
        for index, slot in enumerate(slots, start=1)
    ]


def _ko_existing_schedule_context(case: MileDayMultiTurnCase) -> list[dict[str, str | bool]]:
    return [
        {
            "제목": item.title,
            "날짜": item.scheduled_date,
            "색상": item.color,
            "완료여부": "예" if item.is_completed else "아니오",
        }
        for item in case.input.existing_schedule
    ]


def mileday_multiturn_reference_date_context() -> dict[str, str]:
    today = date.today()
    day_of_week = date_day_of_week(today.isoformat())
    return {
        "today": today.isoformat(),
        "weekday": ko_weekday(day_of_week),
        "day_of_week": day_of_week or "",
        "timezone": MILEDAY_MULTITURN_REFERENCE_TIMEZONE,
    }


def mileday_multiturn_allowed_slots(case: MileDayMultiTurnCase) -> list[dict[str, str]]:
    start_date = date.today()
    end_date = date.fromisoformat(case.expected.constraints.latest_allowed_date)
    availability_by_day = {item.day_of_week: item for item in case.input.availability}
    slots: list[dict[str, str]] = []
    slot_index = 1
    current = start_date
    while current <= end_date:
        day_of_week = date_day_of_week(current.isoformat())
        window = availability_by_day.get(day_of_week or "")
        if window is not None:
            weekday_ko = ko_weekday(day_of_week)
            time_range = f"{window.start_time}-{window.end_time}"
            slots.append(
                {
                    "slot_id": f"S{slot_index:03d}",
                    "scheduled_date": current.isoformat(),
                    "day_of_week": day_of_week,
                    "weekday": weekday_ko,
                    "time_range": time_range,
                    "title_prefix": canonical_title_prefix(day_of_week or "", window.start_time, window.end_time),
                }
            )
            slot_index += 1
        current = date.fromordinal(current.toordinal() + 1)
    return slots
