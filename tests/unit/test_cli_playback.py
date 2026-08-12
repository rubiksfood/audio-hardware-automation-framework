"""Tests for the validate-playback CLI command."""

import json
from pathlib import Path

import numpy as np
from pytest import MonkeyPatch

from audio_hw_framework.audio import AudioBuffer, write_wav
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.cli import app
from audio_hw_framework.device.models import AudioDevice, StreamConfig
from tests.unit.cli_helpers import (
    create_test_device,
    runner,
    write_playback_config,
)


def test_validate_playback_displays_success(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "playback.yaml"
    input_file = tmp_path / "input.wav"

    write_playback_config(config_path)

    write_wav(
        input_file,
        AudioBuffer(
            samples=np.zeros(
                (48, 2),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
    )

    playback_calls: list[AudioBuffer] = []

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

    def fake_playback(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> None:
        playback_calls.append(audio)

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
        "playback",
        fake_playback,
    )

    result = runner.invoke(
        app,
        [
            "validate-playback",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
        ],
    )

    assert result.exit_code == 0
    assert "Playback validation passed" in result.stdout
    assert "Focusrite Scarlett 2i2 USB" in result.stdout
    assert "48000 Hz" in result.stdout
    assert "48" in result.stdout

    assert len(playback_calls) == 1
    assert playback_calls[0].frame_count == 48


def test_validate_playback_outputs_json(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "playback.yaml"
    input_file = tmp_path / "input.wav"

    write_playback_config(config_path)

    write_wav(
        input_file,
        AudioBuffer(
            samples=np.zeros(
                (48, 2),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
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

    def fake_playback(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> None:
        return None

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
        "playback",
        fake_playback,
    )

    result = runner.invoke(
        app,
        [
            "validate-playback",
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
    assert payload["backend"]["name"] == "portaudio"
    assert payload["playback"]["input_file"] == str(input_file)
    assert payload["playback"]["sample_rate"] == 48_000
    assert payload["playback"]["channels"] == 2
    assert payload["playback"]["frames"] == 48


def test_validate_playback_handles_missing_input_file(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "playback.yaml"
    input_file = tmp_path / "missing.wav"

    write_playback_config(config_path)

    result = runner.invoke(
        app,
        [
            "validate-playback",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
        ],
    )

    assert result.exit_code == 2
    assert "Could not read WAV file" in result.stderr


def test_validate_playback_handles_backend_error(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "playback.yaml"
    input_file = tmp_path / "input.wav"

    write_playback_config(config_path)

    write_wav(
        input_file,
        AudioBuffer(
            samples=np.zeros(
                (48, 2),
                dtype=np.float32,
            ),
            sample_rate=48_000,
        ),
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

    def fail_playback(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> None:
        raise AudioBackendError(
            "Playback failed",
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
        "playback",
        fail_playback,
    )

    result = runner.invoke(
        app,
        [
            "validate-playback",
            "--config",
            str(config_path),
            "--input",
            str(input_file),
        ],
    )

    assert result.exit_code == 2
    assert "Playback failed" in result.stderr
