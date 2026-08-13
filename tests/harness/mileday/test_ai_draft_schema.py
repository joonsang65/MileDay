from harness.mileday.ai_draft_schema import ai_schedule_draft_response_schema


def test_ai_draft_response_schema_excludes_mutation_fields():
    schema = ai_schedule_draft_response_schema()

    assert schema["required"] == ["goal", "milestones", "planning_preference"]
    assert set(schema["properties"]) == {"goal", "milestones", "planning_preference"}
    assert "selected_slot_ids" not in schema["properties"]
    assert "db_payload" not in schema["properties"]
    assert schema["properties"]["planning_preference"]["properties"]["intensity"]["enum"] == [
        "relaxed",
        "balanced",
        "intensive",
    ]
