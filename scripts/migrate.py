from pathlib import Path
import os

import psycopg
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


def get_database_url() -> str:
    load_dotenv(BASE_DIR / ".env")
    database_url = os.getenv("SUPABASE_DB_URL")

    if not database_url:
        raise RuntimeError("SUPABASE_DB_URL is not set.")

    return database_url


def ensure_migrations_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            create table if not exists public.schema_migrations (
              id serial primary key,
              filename text not null unique,
              executed_at timestamptz not null default now()
            );
            """
        )


def get_executed_migrations(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("select filename from public.schema_migrations;")
        rows = cur.fetchall()

    return {row[0] for row in rows}


def run_migration(conn: psycopg.Connection, migration_file: Path) -> None:
    sql = migration_file.read_text(encoding="utf-8")

    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            """
            insert into public.schema_migrations (filename)
            values (%s);
            """,
            (migration_file.name,),
        )


def main() -> None:
    database_url = get_database_url()
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not migration_files:
        print("No migration files found.")
        return

    with psycopg.connect(database_url) as conn:
        try:
            ensure_migrations_table(conn)
            executed_migrations = get_executed_migrations(conn)

            pending_files = [
                file for file in migration_files
                if file.name not in executed_migrations
            ]

            if not pending_files:
                print("All migrations are already applied.")
                return

            for migration_file in pending_files:
                print(f"Running migration: {migration_file.name}")
                run_migration(conn, migration_file)

            conn.commit()
            print("All pending migrations applied successfully.")

        except Exception as error:
            conn.rollback()
            print("Migration failed. Rolled back changes.")
            print(error)
            raise


if __name__ == "__main__":
    main()

