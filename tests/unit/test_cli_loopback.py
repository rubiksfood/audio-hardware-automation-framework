"""Tests for the validate-loopback CLI command."""

import json
from pathlib import Path

import numpy as np
import pytest
from pytest import MonkeyPatch

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.sounddevice_backend import (
    SoundDeviceBackend,
)
from audio_hw_framework.cli import app
from audio_hw_framework.device.models import (
    AudioDevice,
    StreamConfig,
)
from tests.unit.cli_helpers import (
    create_test_device,
    runner,
    write_loopback_config,
)

SAMPLE_RATE = 48_000
SIGNAL_DURATION_SECONDS = 0.01
PADDING_SECONDS = 0.001
FREQUENCY_HZ = 1_000.0
AMPLITUDE = 0.25


def create_loopback_capture(
    *,
    amplitude: float = AMPLITUDE,
    frequency_hz: float = FREQUENCY_HZ,
) -> AudioBuffer:
    """Create deterministic stereo loopback capture data."""

    signal_frames = round(SIGNAL_DURATION_SECONDS * SAMPLE_RATE)

    padding_frames = round(PADDING_SECONDS * SAMPLE_RATE)

    total_frames = signal_frames + (2 * padding_frames)

    time_seconds = (
        np.arange(
            signal_frames,
            dtype=np.float64,
        )
        / SAMPLE_RATE
    )

    tone = (amplitude * np.sin(2.0 * np.pi * frequency_hz * time_seconds)).astype(
        np.float32,
    )

    samples = np.zeros(
        (
            total_frames,
            2,
        ),
        dtype=np.float32,
    )

    signal_end = padding_frames + signal_frames

    samples[
        padding_frames:signal_end,
        1,
    ] = tone

    return AudioBuffer(
        samples=samples,
        sample_rate=SAMPLE_RATE,
    )


def patch_loopback_backend(
    monkeypatch: MonkeyPatch,
    *,
    captured_audio: AudioBuffer,
) -> None:
    """Configure the PortAudio backend for hardware-independent CLI tests."""

    device = create_test_device()

    def fake_list_devices(
        self: SoundDeviceBackend,
    ) -> list[AudioDevice]:
        return [device]

    def accept_stream(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        return None

    def fake_duplex(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> AudioBuffer:
        assert selected_device == device
        assert config.sample_rate == SAMPLE_RATE
        assert audio.channel_count == 2
        assert timeout_seconds == 5.0

        return captured_audio

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )

    monkeypatch.setattr(
        SoundDeviceBackend,
        "validate_stream_capability",
        accept_stream,
    )

    monkeypatch.setattr(
        SoundDeviceBackend,
        "validate_stream_opening",
        accept_stream,
    )

    monkeypatch.setattr(
        SoundDeviceBackend,
        "duplex",
        fake_duplex,
    )


def test_validate_loopback_displays_success(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "loopback.yaml"

    write_loopback_config(
        config_path,
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=create_loopback_capture(),
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0

    assert "Loopback validation passed" in result.stdout
    assert "Focusrite Scarlett 2i2 USB" in result.stdout
    assert "Expected frequency" in result.stdout
    assert "Measured frequency" in result.stdout
    assert "RMS" in result.stdout
    assert "Peak" in result.stdout


def test_validate_loopback_returns_one_when_validation_fails(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "loopback.yaml"

    write_loopback_config(
        config_path,
    )

    silent_capture = AudioBuffer(
        samples=np.zeros(
            create_loopback_capture().samples.shape,
            dtype=np.float32,
        ),
        sample_rate=SAMPLE_RATE,
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=silent_capture,
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 1

    assert "Loopback validation failed" in result.stdout
    assert "Loopback failures" in result.stdout
    assert "frequency" in result.stdout
    assert "silence" in result.stdout


def test_validate_loopback_outputs_json(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "loopback.yaml"

    write_loopback_config(
        config_path,
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=create_loopback_capture(),
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
            "--json",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(
        result.stdout,
    )

    assert payload["status"] == "passed"

    assert payload["backend"]["name"] == "portaudio"

    assert payload["device"]["name"] == "Focusrite Scarlett 2i2 USB"

    assert payload["stream"]["sample_rate"] == SAMPLE_RATE

    assert payload["routing"]["output_channel_index"] == 1
    assert payload["routing"]["input_channel_index"] == 1

    assert payload["audio"]["playback"]["channels"] == 2
    assert payload["audio"]["captured"]["channels"] == 2
    assert payload["audio"]["analysed"]["channels"] == 1

    assert payload["frequency"]["expected_hz"] == FREQUENCY_HZ
    assert payload["frequency"]["measured_hz"] == pytest.approx(
        FREQUENCY_HZ,
        abs=0.5,
    )
    assert payload["frequency"]["passed"] is True

    assert payload["metrics"]["silence"]["detected"] is False
    assert payload["metrics"]["clipping"]["detected"] is False

    assert payload["failures"] == []


def test_validate_loopback_json_reports_structured_failures(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "loopback.yaml"

    write_loopback_config(
        config_path,
    )

    silent_capture = AudioBuffer(
        samples=np.zeros(
            create_loopback_capture().samples.shape,
            dtype=np.float32,
        ),
        sample_rate=SAMPLE_RATE,
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=silent_capture,
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
            "--json",
        ],
    )

    assert result.exit_code == 1

    payload = json.loads(
        result.stdout,
    )

    assert payload["status"] == "failed"
    assert payload["frequency"]["passed"] is False

    frequency_failures = [
        failure for failure in payload["failures"] if failure["metric"] == "frequency"
    ]

    silence_failures = [
        failure for failure in payload["failures"] if failure["metric"] == "silence"
    ]

    assert len(frequency_failures) == 1
    assert len(silence_failures) == 1

    assert frequency_failures[0]["channel"] == 1
    assert frequency_failures[0]["expected"] == FREQUENCY_HZ
    assert frequency_failures[0]["threshold"] == 5.0

    assert silence_failures[0]["channel"] == 1


def test_validate_loopback_handles_missing_configuration(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.yaml"

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(missing_path),
        ],
    )

    assert result.exit_code == 2
    assert "Configuration file not found" in result.stderr


def test_validate_loopback_requires_loopback_configuration(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    config_path.write_text(
        """
device:
  name_contains: "Scarlett"
  host_api_contains: "WASAPI"
  minimum_input_channels: 2
  minimum_output_channels: 2

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2
""",
        encoding="utf-8",
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=create_loopback_capture(),
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 2
    assert "Loopback validation settings are required" in result.stderr


def test_validate_loopback_saves_evidence(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "loopback.yaml"

    evidence_directory = tmp_path / "evidence"

    write_loopback_config(
        config_path,
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=create_loopback_capture(),
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
            "--evidence-dir",
            str(evidence_directory),
        ],
    )

    assert result.exit_code == 0

    assert "Evidence saved to:" in result.stdout

    assert (evidence_directory / "report.json").is_file()

    assert (evidence_directory / "playback.wav").is_file()

    assert (evidence_directory / "captured.wav").is_file()

    assert (evidence_directory / "analysed.wav").is_file()


def test_validate_loopback_saves_evidence_when_validation_fails(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "loopback.yaml"

    evidence_directory = tmp_path / "failed-evidence"

    write_loopback_config(
        config_path,
    )

    silent_capture = AudioBuffer(
        samples=np.zeros(
            create_loopback_capture().samples.shape,
            dtype=np.float32,
        ),
        sample_rate=SAMPLE_RATE,
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=silent_capture,
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
            "--evidence-dir",
            str(evidence_directory),
        ],
    )

    assert result.exit_code == 1

    assert (evidence_directory / "report.json").is_file()

    assert (evidence_directory / "playback.wav").is_file()

    assert (evidence_directory / "captured.wav").is_file()

    assert (evidence_directory / "analysed.wav").is_file()

    payload = json.loads(
        (evidence_directory / "report.json").read_text(
            encoding="utf-8",
        )
    )

    assert payload["status"] == "failed"
    assert payload["failures"]


def test_validate_loopback_json_includes_evidence_paths(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "loopback.yaml"

    evidence_directory = tmp_path / "evidence"

    write_loopback_config(
        config_path,
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=create_loopback_capture(),
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
            "--json",
            "--evidence-dir",
            str(evidence_directory),
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(
        result.stdout,
    )

    assert payload["artifacts"]["playback_wav"] == str(evidence_directory / "playback.wav")

    assert payload["artifacts"]["captured_wav"] == str(evidence_directory / "captured.wav")

    assert payload["artifacts"]["analysed_wav"] == str(evidence_directory / "analysed.wav")


def test_validate_loopback_reports_evidence_write_error(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "loopback.yaml"

    invalid_directory = tmp_path / "not-a-directory"

    invalid_directory.write_text(
        "existing file",
        encoding="utf-8",
    )

    write_loopback_config(
        config_path,
    )

    patch_loopback_backend(
        monkeypatch,
        captured_audio=create_loopback_capture(),
    )

    result = runner.invoke(
        app,
        [
            "validate-loopback",
            "--config",
            str(config_path),
            "--evidence-dir",
            str(invalid_directory),
        ],
    )

    assert result.exit_code == 2

    assert "Could not save loopback evidence" in result.stderr
