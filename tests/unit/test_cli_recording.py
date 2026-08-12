"""Tests for the validate-recording CLI command."""

import json
from pathlib import Path

import numpy as np
from pytest import MonkeyPatch

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.cli import app
from audio_hw_framework.device.models import AudioDevice, StreamConfig
from tests.unit.cli_helpers import (
    create_test_device,
    runner,
    write_recording_config,
)


def test_validate_recording_displays_success(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "recording.yaml"

    write_recording_config(config_path)

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

    def fake_record(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        return AudioBuffer(
            samples=np.zeros(
                (frame_count, config.input_channels),
                dtype=np.float32,
            ),
            sample_rate=config.sample_rate,
        )

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
        "record",
        fake_record,
    )

    result = runner.invoke(
        app,
        [
            "validate-recording",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert "Recording validation passed" in result.stdout
    assert "Focusrite Scarlett 2i2 USB" in result.stdout
    assert "48000 Hz" in result.stdout
    assert "48" in result.stdout


def test_validate_recording_outputs_json(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "recording.yaml"

    write_recording_config(config_path)

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

    def fake_record(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        return AudioBuffer(
            samples=np.zeros(
                (frame_count, config.input_channels),
                dtype=np.float32,
            ),
            sample_rate=config.sample_rate,
        )

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
        "record",
        fake_record,
    )

    result = runner.invoke(
        app,
        [
            "validate-recording",
            "--config",
            str(config_path),
            "--json",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["status"] == "passed"
    assert payload["backend"]["name"] == "portaudio"
    assert payload["device"]["name"] == "Focusrite Scarlett 2i2 USB"
    assert payload["recording"]["sample_rate"] == 48_000
    assert payload["recording"]["channels"] == 2
    assert payload["recording"]["frames"] == 48


def test_validate_recording_exports_wav(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "recording.yaml"
    output_file = tmp_path / "capture.wav"

    write_recording_config(
        config_path,
        output_file=output_file,
    )

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

    def fake_record(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        return AudioBuffer(
            samples=np.zeros(
                (frame_count, config.input_channels),
                dtype=np.float32,
            ),
            sample_rate=config.sample_rate,
        )

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
        "record",
        fake_record,
    )

    result = runner.invoke(
        app,
        [
            "validate-recording",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert output_file.is_file()


def test_validate_recording_handles_backend_error(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "recording.yaml"

    write_recording_config(config_path)

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

    def fail_recording(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        raise AudioBackendError(
            "Recording failed",
        )

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
        "record",
        fail_recording,
    )

    result = runner.invoke(
        app,
        [
            "validate-recording",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 2
    assert "Recording failed" in result.stderr
