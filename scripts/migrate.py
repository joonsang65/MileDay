from pathlib import Path
import os
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


def log(message: str) -> None:
    print(f"[migrate] {message}", flush=True)


def get_safe_database_target(database_url: str) -> str:
    try:
        parsed = urlparse(database_url)
        host = parsed.hostname or "unknown-host"
        port = parsed.port or 5432
        database = parsed.path.lstrip("/") or "unknown-database"
        username = parsed.username or "unknown-user"
    except ValueError:
        return "invalid SUPABASE_DB_URL format"

    return f"{username}@{host}:{port}/{database}"


def get_database_url() -> str:
    log(f"Loading environment variables from {BASE_DIR / '.env'}")
    load_dotenv(BASE_DIR / ".env")
    database_url = os.getenv("SUPABASE_DB_URL")

    if not database_url:
        raise RuntimeError("SUPABASE_DB_URL is not set.")

    log(f"SUPABASE_DB_URL found for {get_safe_database_target(database_url)}")
    return database_url


def ensure_migrations_table(conn: psycopg.Connection) -> None:
    log("Ensuring public.schema_migrations table exists.")
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
    log("Reading already executed migrations.")
    with conn.cursor() as cur:
        cur.execute("select filename from public.schema_migrations;")
        rows = cur.fetchall()

    executed = {row[0] for row in rows}
    log(f"Found {len(executed)} executed migration(s).")
    return executed


def run_migration(conn: psycopg.Connection, migration_file: Path) -> None:
    log(f"Reading SQL file: {migration_file.name}")
    sql = migration_file.read_text(encoding="utf-8")

    with conn.cursor() as cur:
        log(f"Executing migration: {migration_file.name}")
        cur.execute(sql)
        cur.execute(
            """
            insert into public.schema_migrations (filename)
            values (%s);
            """,
            (migration_file.name,),
        )
    log(f"Recorded migration: {migration_file.name}")


def main() -> None:
    log("Starting Supabase schema migration.")
    database_url = get_database_url()
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    log(f"Migration directory: {MIGRATIONS_DIR}")
    log(f"Discovered {len(migration_files)} migration file(s).")

    if not migration_files:
        log("No migration files found.")
        return

    try:
        log("Connecting to Supabase Postgres.")
        with psycopg.connect(database_url) as conn:
            log("Database connection established.")
            try:
                ensure_migrations_table(conn)
                executed_migrations = get_executed_migrations(conn)

                pending_files = [
                    file for file in migration_files
                    if file.name not in executed_migrations
                ]

                if not pending_files:
                    log("All migrations are already applied.")
                    return

                log(f"Pending migration count: {len(pending_files)}")
                for migration_file in pending_files:
                    run_migration(conn, migration_file)

                log("Committing migration transaction.")
                conn.commit()
                log("All pending migrations applied successfully.")

            except Exception as error:
                conn.rollback()
                log("Migration failed. Rolled back changes.")
                log(f"Error: {error}")
                raise

    except psycopg.OperationalError as error:
        log("Database connection failed.")
        log(f"Error: {error}")
        raise


if __name__ == "__main__":
    main()
