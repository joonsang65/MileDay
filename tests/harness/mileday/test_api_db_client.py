from harness.mileday.api_db_client import ApiDbWriter


class _Response:
    def __init__(self, data):
        self.data = data


class _Table:
    def __init__(self, client, name):
        self.client = client
        self.name = name
        self.operation = None
        self.payload = None
        self.filters = []

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def execute(self):
        if self.operation == "insert":
            self.client.inserts.append((self.name, self.payload))
            if self.name == "goals":
                return _Response([{"id": "goal-1"}])
            count = len(self.payload) if isinstance(self.payload, list) else 1
            offset = self.client.next_milestone_id
            self.client.next_milestone_id += count
            return _Response([{"id": f"milestone-{index}"} for index in range(offset, offset + count)])
        if self.operation == "update":
            self.client.updates.append((self.name, self.payload, self.filters))
            return _Response([{"id": "updated"}])
        self.client.deletes.append((self.name, self.filters))
        return _Response([{"id": "deleted"}])


class _Client:
    def __init__(self):
        self.inserts = []
        self.updates = []
        self.deletes = []
        self.next_milestone_id = 1

    def table(self, name):
        return _Table(self, name)


def test_api_db_writer_inserts_prefixed_goal_and_milestones():
    client = _Client()
    writer = ApiDbWriter(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        user_id="user-1",
        title_prefix="[TEST]",
        client=client,
    )

    record = writer.insert_create_payload(
        run_id="prompt-test-1",
        case_id="case-1-turn-1",
        turn_id=1,
        plan_items=[{"slot_id": "S001"}, {"slot_id": "S002"}],
        payload={
            "goal": {
                "title": "시험 준비",
                "deadline": "2026-09-01",
                "is_recurring": False,
                "recurrence_type": None,
                "color": "#4F46E5",
            },
            "milestones": [
                {"title": "[월 19:00-21:00] 기초 정리", "color": "#4F46E5", "scheduled_date": "2026-08-17"},
                {"title": "[화 19:00-21:00] 문제 풀이", "color": "#4F46E5", "scheduled_date": "2026-08-18"},
            ],
        },
    )

    assert record.goal_id == "goal-1"
    assert record.milestone_ids == ["milestone-1", "milestone-2"]
    assert record.milestone_slot_ids == {"S001": "milestone-1", "S002": "milestone-2"}
    assert record.milestone_titles == {
        "S001": "[TEST] [월 19:00-21:00] 기초 정리",
        "S002": "[TEST] [화 19:00-21:00] 문제 풀이",
    }
    goal_insert = client.inserts[0][1]
    milestone_insert = client.inserts[1][1]
    assert goal_insert["user_id"] == "user-1"
    assert goal_insert["title"] == "[TEST] 시험 준비"
    assert milestone_insert[0]["goal_id"] == "goal-1"
    assert milestone_insert[0]["title"] == "[TEST] [월 19:00-21:00] 기초 정리"


def test_api_db_writer_updates_partial_milestone_with_prefixed_title():
    client = _Client()
    writer = ApiDbWriter(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        user_id="user-1",
        title_prefix="[TEST]",
        client=client,
    )

    record = writer.update_partial_payload(
        run_id="prompt-test-1",
        case_id="case-1-turn-2",
        turn_id=2,
        create_record={
            "goal_id": "goal-1",
            "milestone_slot_ids": {"S001": "milestone-1", "S002": "milestone-2"},
            "goal_title": "[TEST] 시험 준비",
            "user_id": "user-1",
        },
        parsed_json={
            "patch_items": [{"slot_id": "S002", "task": "심화 문제 풀이"}],
            "add_items": [],
            "remove_slot_ids": [],
            "plan_items": [
                {"slot_id": "S001", "task": "기초 정리"},
                {"slot_id": "S002", "task": "심화 문제 풀이"},
            ],
            "db_payload": {
                "milestones": [
                    {"title": "[월 19:00-21:00] 기초 정리"},
                    {"title": "[화 19:00-21:00] 심화 문제 풀이"},
                ]
            },
        },
    )

    assert record.operation == "rename"
    assert record.milestone_ids == ["milestone-2"]
    assert record.milestone_titles == {"S002": "[TEST] [화 19:00-21:00] 심화 문제 풀이"}
    assert client.updates == [
        (
            "milestones",
            {"title": "[TEST] [화 19:00-21:00] 심화 문제 풀이"},
            [("id", "milestone-2"), ("goal_id", "goal-1"), ("user_id", "user-1")],
        )
    ]


def test_api_db_writer_adds_partial_milestone():
    client = _Client()
    writer = ApiDbWriter(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        user_id="user-1",
        title_prefix="[TEST]",
        client=client,
    )

    record = writer.update_partial_payload(
        run_id="prompt-test-1",
        case_id="case-1-turn-2",
        turn_id=2,
        create_record={
            "goal_id": "goal-1",
            "milestone_slot_ids": {"S001": "milestone-1", "S002": "milestone-2"},
            "goal_title": "[TEST] 시험 준비",
            "user_id": "user-1",
        },
        parsed_json={
            "patch_items": [],
            "add_items": [{"slot_id": "S003", "task": "오답 정리"}],
            "remove_slot_ids": [],
            "plan_items": [
                {"slot_id": "S001", "task": "기초 정리"},
                {"slot_id": "S002", "task": "문제 풀이"},
                {"slot_id": "S003", "task": "오답 정리"},
            ],
            "db_payload": {
                "milestones": [
                    {"title": "[월 19:00-21:00] 기초 정리"},
                    {"title": "[화 19:00-21:00] 문제 풀이"},
                    {"title": "[수 19:00-21:00] 오답 정리", "color": "#4F46E5", "scheduled_date": "2026-08-19"},
                ]
            },
        },
    )

    assert record is not None
    assert record.operation == "add"
    assert record.milestone_slot_ids == {"S003": "milestone-1"}
    assert record.milestone_titles == {"S003": "[TEST] [수 19:00-21:00] 오답 정리"}
    assert client.inserts == [
        (
            "milestones",
            [
                {
                    "goal_id": "goal-1",
                    "user_id": "user-1",
                    "title": "[TEST] [수 19:00-21:00] 오답 정리",
                    "color": "#4F46E5",
                    "scheduled_date": "2026-08-19",
                    "is_completed": False,
                }
            ],
        )
    ]


def test_api_db_writer_removes_partial_milestone():
    client = _Client()
    writer = ApiDbWriter(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        user_id="user-1",
        title_prefix="[TEST]",
        client=client,
    )

    record = writer.update_partial_payload(
        run_id="prompt-test-1",
        case_id="case-1-turn-2",
        turn_id=2,
        create_record={
            "goal_id": "goal-1",
            "milestone_slot_ids": {"S001": "milestone-1", "S002": "milestone-2"},
            "goal_title": "[TEST] 시험 준비",
            "user_id": "user-1",
        },
        parsed_json={
            "patch_items": [],
            "add_items": [],
            "remove_slot_ids": ["S002"],
            "plan_items": [{"slot_id": "S001", "task": "기초 정리"}],
            "db_payload": {"milestones": [{"title": "[월 19:00-21:00] 기초 정리"}]},
        },
    )

    assert record is not None
    assert record.operation == "remove"
    assert record.milestone_ids == ["milestone-2"]
    assert record.milestone_slot_ids == {"S002": "milestone-2"}
    assert client.deletes == [
        ("milestones", [("id", "milestone-2"), ("goal_id", "goal-1"), ("user_id", "user-1")])
    ]


def test_api_db_writer_skips_no_op_partial_update():
    client = _Client()
    writer = ApiDbWriter(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        user_id="user-1",
        title_prefix="[TEST]",
        client=client,
    )

    record = writer.update_partial_payload(
        run_id="prompt-test-1",
        case_id="case-1-turn-2",
        turn_id=2,
        create_record={
            "goal_id": "goal-1",
            "milestone_slot_ids": {"S001": "milestone-1"},
            "goal_title": "[TEST] 시험 준비",
            "user_id": "user-1",
        },
        parsed_json={
            "patch_items": [],
            "add_items": [],
            "remove_slot_ids": [],
            "plan_items": [{"slot_id": "S001", "task": "기초 정리"}],
            "db_payload": {"milestones": [{"title": "[월 19:00-21:00] 기초 정리"}]},
        },
    )

    assert record is None
    assert client.inserts == []
    assert client.updates == []
    assert client.deletes == []


def test_api_db_writer_cleanup_deletes_manifest_ids_with_user_filter():
    client = _Client()
    writer = ApiDbWriter(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        user_id="user-1",
        title_prefix="[TEST]",
        client=client,
    )

    counts = writer.cleanup_record(
        {
            "goal_id": "goal-1",
            "milestone_ids": ["milestone-1", "milestone-2"],
            "user_id": "user-1",
        }
    )

    assert counts == {"goals": 1, "milestones": 2}
    assert client.deletes == [
        ("milestones", [("id", "milestone-1"), ("user_id", "user-1")]),
        ("milestones", [("id", "milestone-2"), ("user_id", "user-1")]),
        ("goals", [("id", "goal-1"), ("user_id", "user-1")]),
    ]
