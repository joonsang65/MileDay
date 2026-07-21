from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from harness.config import load_settings
from harness.dataset_processor import DatasetProcessingError, prepare_all_datasets
from harness.dataset_registry import DEFAULT_DATASET_REGISTRY_PATH
from harness.model_registry import (
    DEFAULT_MODEL_REGISTRY_PATH,
    check_model_availability,
    load_model_registry,
)
from harness.runtime.base import RuntimeAdapterError
from harness.runtime.ollama import OllamaRuntime


app = typer.Typer(help="Local LLM evaluation harness.")


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
            typer.echo(f"ollama_status=unavailable")
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
    """List configured model candidates without substituting missing models."""

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


@app.command("prepare-datasets")
def prepare_datasets(
    registry: Annotated[
        Path,
        typer.Option(
            "--registry",
            "-r",
            help="Dataset registry YAML path.",
        ),
    ] = DEFAULT_DATASET_REGISTRY_PATH,
    sample_limit: Annotated[
        int | None,
        typer.Option("--sample-limit", help="Optional positive row limit per dataset."),
    ] = None,
    dataset: Annotated[
        str | None,
        typer.Option("--dataset", help="Optional single dataset key from configs/datasets.yaml."),
    ] = None,
) -> None:
    """Convert pinned source snapshots into local processed JSONL files."""

    try:
        loaded_registry = None
        if dataset is not None:
            from harness.dataset_registry import load_dataset_registry

            loaded_registry = load_dataset_registry(registry)
            if dataset not in loaded_registry.datasets:
                raise typer.BadParameter(f"Unknown dataset key: {dataset}")
            loaded_registry.datasets = {
                dataset: loaded_registry.datasets[dataset],
            }
        processed = prepare_all_datasets(
            registry=loaded_registry,
            registry_path=registry,
            sample_limit=sample_limit,
        )
    except (FileNotFoundError, ValueError, DatasetProcessingError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo("dataset\trows\tprocessed_path")
    for item in processed:
        typer.echo(f"{item.dataset_key}\t{item.row_count}\t{item.processed_path}")


if __name__ == "__main__":
    app()
