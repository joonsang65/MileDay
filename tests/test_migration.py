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
    assert "revoke all on schema supabase_migrations from anon" in sql
    assert "revoke all on schema supabase_migrations from authenticated" in sql
    assert "grant usage on schema supabase_migrations to postgres" in sql

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


def test_backfill_migration_adds_color_columns_to_existing_tables() -> None:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "supabase"
        / "migrations"
        / "202607090001_backfill_goal_milestone_color_columns.sql"
    )
    sql = sql_path.read_text(encoding="utf-8").lower()

    assert "alter table if exists public.goals" in sql
    assert "add column if not exists color text not null default '#4f46e5'" in sql
    assert "alter table if exists public.milestones" in sql
    assert "add column if not exists color text not null default '#f97316'" in sql
    assert "notify pgrst, 'reload schema'" in sql


def test_recurrence_type_migration_allows_null_for_non_recurring_goals() -> None:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "supabase"
        / "migrations"
        / "202607090002_fix_goal_recurrence_type_nullability.sql"
    )
    sql = sql_path.read_text(encoding="utf-8").lower()

    assert "alter table if exists public.goals" in sql
    assert "alter column recurrence_type drop not null" in sql
    assert "goals_recurrence_type_state" in sql
    assert "is_recurring = true and recurrence_type in ('daily', 'weekly', 'monthly')" in sql
    assert "is_recurring = false and recurrence_type is null" in sql
    assert "notify pgrst, 'reload schema'" in sql
