"""Tests for the analyse-audio CLI command."""

import json
from pathlib import Path

import numpy as np

from audio_hw_framework.audio import AudioBuffer, write_wav
from audio_hw_framework.cli import app
from tests.unit.cli_helpers import (
    runner,
    write_analysis_config,
)


def test_analyse_audio_passes_configured_thresholds(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "analysis.yaml"
    input_file = tmp_path / "input.wav"

    write_analysis_config(
        config_path,
        minimum_rms=0.1,
        maximum_peak=0.5,
    )

    write_wav(
        input_file,
        AudioBuffer(
            samples=np.array(
                [
                    [0.25, 0.25],
                    [-0.25, -0.25],
                ],
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    result = runner.invoke(
        app,
        [
            "analyse-audio",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
        ],
    )

    assert result.exit_code == 0
    assert "Audio analysis passed" in result.stdout
    assert "RMS" in result.stdout
    assert "Peak" in result.stdout
    assert "DC offset" in result.stdout


def test_analyse_audio_returns_one_when_threshold_fails(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "analysis.yaml"
    input_file = tmp_path / "input.wav"

    write_analysis_config(
        config_path,
        minimum_rms=0.5,
    )

    write_wav(
        input_file,
        AudioBuffer(
            samples=np.array(
                [
                    [0.25],
                    [-0.25],
                ],
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    result = runner.invoke(
        app,
        [
            "analyse-audio",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
        ],
    )

    assert result.exit_code == 1
    assert "Audio analysis failed" in result.stdout
    assert "Threshold failures" in result.stdout
    assert "rms" in result.stdout


def test_analyse_audio_outputs_json(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "analysis.yaml"
    input_file = tmp_path / "input.wav"

    write_analysis_config(
        config_path,
        minimum_rms=0.1,
        maximum_peak=0.5,
    )

    write_wav(
        input_file,
        AudioBuffer(
            samples=np.array(
                [
                    [0.25],
                    [-0.25],
                ],
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    result = runner.invoke(
        app,
        [
            "analyse-audio",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
            "--json",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["status"] == "passed"
    assert payload["input_file"] == str(input_file)
    assert payload["audio"]["sample_rate"] == 48_000
    assert payload["audio"]["channels"] == 1
    assert payload["audio"]["frames"] == 2

    assert payload["metrics"]["rms"]["overall"] == 0.25
    assert payload["metrics"]["peak"]["overall"] == 0.25
    assert payload["metrics"]["dc_offset"]["overall"] == 0.0
    assert payload["failures"] == []


def test_analyse_audio_json_reports_structured_failure(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "analysis.yaml"
    input_file = tmp_path / "input.wav"

    write_analysis_config(
        config_path,
        minimum_rms=0.5,
    )

    write_wav(
        input_file,
        AudioBuffer(
            samples=np.array(
                [
                    [0.25],
                    [-0.25],
                ],
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    result = runner.invoke(
        app,
        [
            "analyse-audio",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
            "--json",
        ],
    )

    assert result.exit_code == 1

    payload = json.loads(result.stdout)

    assert payload["status"] == "failed"
    assert len(payload["failures"]) == 1

    failure = payload["failures"][0]

    assert failure["metric"] == "rms"
    assert failure["channel"] == 0
    assert failure["threshold"] == 0.5
    assert failure["reason"] == "RMS level is below the configured minimum"


def test_analyse_audio_handles_missing_input_file(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "analysis.yaml"
    input_file = tmp_path / "missing.wav"

    write_analysis_config(config_path)

    result = runner.invoke(
        app,
        [
            "analyse-audio",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
        ],
    )

    assert result.exit_code == 2
    assert "Could not read WAV file" in result.stderr


def test_analyse_audio_handles_invalid_configuration(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "analysis.yaml"
    input_file = tmp_path / "input.wav"

    config_path.write_text(
        """
device:
  name_contains: "Scarlett"

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2

thresholds:
  clipping_threshold: 0
""",
        encoding="utf-8",
    )

    write_wav(
        input_file,
        AudioBuffer(
            samples=np.zeros(
                (2, 1),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    result = runner.invoke(
        app,
        [
            "analyse-audio",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
        ],
    )

    assert result.exit_code == 2
    assert "Invalid configuration" in result.stderr
