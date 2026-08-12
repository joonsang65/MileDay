from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from harness.config import load_settings
from harness.mileday.api_constants import MILEDAY_MULTITURN_FIXTURE
from harness.mileday.api_runner import (
    MILEDAY_API_MODEL_ID,
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    MILEDAY_API_SLEEP_SECONDS,
    cleanup_prompt_test_api,
    run_prompt_test_api,
)
from harness.model_registry import (
    DEFAULT_MODEL_REGISTRY_PATH,
    check_model_availability,
    load_model_registry,
)
from harness.runtime.base import RuntimeAdapterError
from harness.runtime.ollama import OllamaRuntime


app = typer.Typer(help="MileDay flash-lite prompt/parser harness.")


@app.callback()
def main() -> None:
    """Run harness commands."""


@app.command()
def preflight(
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Optional EVAL-001 JSON config path."),
    ] = None,
    check_ollama: Annotated[
        bool,
        typer.Option("--check-ollama", help="Check local Ollama API availability."),
    ] = False,
) -> None:
    """Run offline configuration and filesystem checks."""

    settings = load_settings(config)
    typer.echo("MileDay harness preflight")
    typer.echo(f"project_root={settings.project_root}")
    typer.echo(f"artifacts_dir={settings.artifacts_dir}")
    typer.echo(f"runs_dir={settings.runs_dir}")
    typer.echo(f"datasets_dir={settings.datasets_dir}")
    typer.echo(f"default_timeout_seconds={settings.default_timeout_seconds}")
    typer.echo(f"ollama_base_url={settings.ollama_base_url}")
    if check_ollama:
        runtime = OllamaRuntime(base_url=settings.ollama_base_url)
        try:
            runtime.check_health(timeout_seconds=min(settings.default_timeout_seconds, 5))
        except RuntimeAdapterError as exc:
            typer.echo("ollama_status=unavailable")
            typer.echo(f"ollama_error_category={exc.category}")
            typer.echo(f"ollama_error_message={exc.message}")
        else:
            typer.echo("ollama_status=ok")
    typer.echo("status=ok")


@app.command("list-models")
def list_models(
    registry: Annotated[
        Path,
        typer.Option(
            "--registry",
            "-r",
            help="Model registry YAML path.",
        ),
    ] = DEFAULT_MODEL_REGISTRY_PATH,
    check_installed: Annotated[
        bool,
        typer.Option("--check-installed", help="Check local Ollama installation status."),
    ] = False,
) -> None:
    """List configured local model candidates."""

    try:
        model_registry = load_model_registry(registry)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    availability_by_id = {}
    if check_installed:
        try:
            availability_by_id = {
                item.model_id: item.installed
                for item in check_model_availability(model_registry)
            }
        except (FileNotFoundError, subprocess.SubprocessError, OSError) as exc:
            raise typer.BadParameter(f"Ollama availability check failed: {exc}") from exc

    typer.echo("id\tprovider\truntime\tmodel_tag\tinstalled")
    for model in model_registry.models:
        installed = availability_by_id.get(model.id)
        installed_text = "not_checked" if installed is None else str(installed).lower()
        typer.echo(
            f"{model.id}\t{model.provider}\t{model.runtime}\t"
            f"{model.model_tag}\t{installed_text}"
        )


@app.command("test_api")
def test_api(
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Optional positive limit for fixture cases to execute."),
    ] = None,
    write_no: Annotated[
        bool,
        typer.Option("--write-no", help="Run prompt/parser evaluation without writing DB rows."),
    ] = False,
) -> None:
    """Run the flash-lite MileDay API prompt/parser test."""

    if limit is not None and limit <= 0:
        raise typer.BadParameter("limit must be positive.")
    run_prompt_test_api(
        settings=load_settings(),
        fixture=MILEDAY_MULTITURN_FIXTURE,
        limit=limit,
        write_db=not write_no,
    )


@app.command("cleanup")
def cleanup(
    run_id: Annotated[
        str,
        typer.Option("--run-id", help="Prompt test run id to clean up from DB."),
    ],
) -> None:
    """Delete DB rows created by a prompt-test run manifest."""

    cleanup_prompt_test_api(settings=load_settings(), run_id=run_id)


if __name__ == "__main__":
    app()
