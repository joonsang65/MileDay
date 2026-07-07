from __future__ import annotations

from pathlib import Path


def test_m1_migration_contains_required_tables_and_security_policies() -> None:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "supabase"
        / "migrations"
        / "202607050001_m1_base_schema.sql"
    )
    sql = sql_path.read_text(encoding="utf-8").lower()

    for table in ["public.goals", "public.milestones", "public.user_settings"]:
        assert f"create table if not exists {table}" in sql
        assert f"alter table {table} enable row level security" in sql

    assert "references public.goals(id) on delete cascade" in sql
    assert "references auth.users(id) on delete cascade" in sql
    assert "create or replace function public.set_updated_at()" in sql
    assert "create or replace function public.ensure_milestone_goal_owner()" in sql
    assert "milestone user_id must match goal user_id" in sql
    assert "auth.uid() = user_id" in sql

    for policy in [
        "goals_select_own",
        "goals_insert_own",
        "goals_update_own",
        "goals_delete_own",
        "milestones_select_own",
        "milestones_insert_own",
        "milestones_update_own",
        "milestones_delete_own",
        "user_settings_select_own",
        "user_settings_insert_own",
        "user_settings_update_own",
        "user_settings_delete_own",
    ]:
        assert policy in sql
