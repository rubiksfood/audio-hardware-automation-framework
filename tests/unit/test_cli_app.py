"""Tests for root CLI behaviour."""

from audio_hw_framework.cli import app
from tests.unit.cli_helpers import runner


def test_cli_help() -> None:
    result = runner.invoke(
        app,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "Inspect and validate audio hardware" in result.stdout
