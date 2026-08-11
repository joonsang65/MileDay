from typer.testing import CliRunner

from harness.cli import app


def test_preflight_command_runs():
    result = CliRunner().invoke(app, ["preflight"])

    assert result.exit_code == 0
    assert "MileDay harness preflight" in result.stdout
    assert "status=ok" in result.stdout


def test_preflight_command_accepts_ollama_check(monkeypatch):
    monkeypatch.setattr("harness.cli.OllamaRuntime.check_health", lambda self, timeout_seconds: None)

    result = CliRunner().invoke(app, ["preflight", "--check-ollama"])

    assert result.exit_code == 0
    assert "status=ok" in result.stdout
    assert "ollama_status=ok" in result.stdout


def test_list_models_command_runs_without_install_check():
    result = CliRunner().invoke(app, ["list-models"])

    assert result.exit_code == 0
    assert "candidate-1" in result.stdout
    assert "not_checked" in result.stdout
