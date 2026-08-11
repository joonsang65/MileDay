from harness.mileday.time_prefix import (
    canonical_milestone_title,
    canonical_title_prefix,
    parse_canonical_milestone_title,
)


def test_canonical_title_prefix_uses_fixed_korean_format():
    assert canonical_title_prefix("monday", "19:00", "21:00") == "[월 19:00-21:00]"
    assert (
        canonical_milestone_title("wednesday", "07:30", "08:30", "영어 회화 녹음")
        == "[수 07:30-08:30] 영어 회화 녹음"
    )


def test_parse_canonical_milestone_title_splits_prefix_and_task():
    parsed = parse_canonical_milestone_title("[토 14:00-16:00] 포트폴리오 점검")

    assert parsed is not None
    assert parsed.day_of_week == "saturday"
    assert parsed.start_time == "14:00"
    assert parsed.end_time == "16:00"
    assert parsed.task == "포트폴리오 점검"


def test_parse_canonical_milestone_title_rejects_non_canonical_variants():
    assert parse_canonical_milestone_title("[월요일 7시-9시] 러닝") is None
    assert parse_canonical_milestone_title("[Mon 19:00-21:00] 러닝") is None
    assert parse_canonical_milestone_title("월요일 19:00 러닝") is None
    assert parse_canonical_milestone_title("[월 21:00-19:00] 러닝") is None
