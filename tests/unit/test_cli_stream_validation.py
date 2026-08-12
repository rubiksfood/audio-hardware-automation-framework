"""Tests for the validate-stream CLI command."""

import json
from pathlib import Path

from pytest import MonkeyPatch

from audio_hw_framework.backend.base import (
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.cli import app
from audio_hw_framework.device.models import AudioDevice, StreamConfig
from tests.unit.cli_helpers import (
    create_test_device,
    runner,
    write_test_config,
)


def test_validate_stream_displays_success(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "config.yaml"

    write_test_config(config_path)

    capability_calls: list[AudioDevice] = []
    opening_calls: list[AudioDevice] = []

    def fake_list_devices(
        self: SoundDeviceBackend,
    ) -> list[AudioDevice]:
        return [device]

    def fake_validate_capability(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        capability_calls.append(selected_device)

    def fake_validate_opening(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        opening_calls.append(selected_device)

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )
    monkeypatch.setattr(
        SoundDeviceBackend,
        "validate_stream_capability",
        fake_validate_capability,
    )
    monkeypatch.setattr(
        SoundDeviceBackend,
        "validate_stream_opening",
        fake_validate_opening,
    )

    result = runner.invoke(
        app,
        [
            "validate-stream",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert "Stream validation passed" in result.stdout
    assert "Focusrite Scarlett 2i2 USB" in result.stdout
    assert "WASAPI" in result.stdout
    assert "48000 Hz" in result.stdout
    assert capability_calls == [device]
    assert opening_calls == [device]


def test_validate_stream_outputs_json(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "config.yaml"

    write_test_config(config_path)

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

    result = runner.invoke(
        app,
        [
            "validate-stream",
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
    assert payload["stream"]["sample_rate"] == 48_000
    assert payload["stream"]["block_size"] == 128
    assert payload["stream"]["dtype"] == "float32"
    assert payload["checks"]["capability"] == "passed"
    assert payload["checks"]["stream_opening"] == "passed"


def test_validate_stream_handles_missing_configuration(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.yaml"

    result = runner.invoke(
        app,
        [
            "validate-stream",
            "--config",
            str(missing_path),
        ],
    )

    assert result.exit_code == 2
    assert "Configuration file not found" in result.stderr


def test_validate_stream_handles_no_matching_device(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    write_test_config(config_path)

    def fake_list_devices(
        self: SoundDeviceBackend,
    ) -> list[AudioDevice]:
        return []

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )

    result = runner.invoke(
        app,
        [
            "validate-stream",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 2
    assert "No device matched configuration" in result.stderr


def test_validate_stream_handles_ambiguous_device_match(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    first_device = create_test_device()

    second_device = AudioDevice(
        index=1,
        name="Focusrite Scarlett Solo USB",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    config_path = tmp_path / "config.yaml"

    write_test_config(config_path)

    def fake_list_devices(
        self: SoundDeviceBackend,
    ) -> list[AudioDevice]:
        return [
            first_device,
            second_device,
        ]

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )

    result = runner.invoke(
        app,
        [
            "validate-stream",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 2
    assert "Multiple devices matched configuration" in result.stderr


def test_validate_stream_handles_capability_failure(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "config.yaml"

    write_test_config(config_path)

    def fake_list_devices(
        self: SoundDeviceBackend,
    ) -> list[AudioDevice]:
        return [device]

    def reject_capability(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        raise StreamCapabilityError(
            "Unsupported sample rate",
        )

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )
    monkeypatch.setattr(
        SoundDeviceBackend,
        "validate_stream_capability",
        reject_capability,
    )

    result = runner.invoke(
        app,
        [
            "validate-stream",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 2
    assert "Unsupported sample rate" in result.stderr


def test_validate_stream_handles_opening_failure(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()
    config_path = tmp_path / "config.yaml"

    write_test_config(config_path)

    def fake_list_devices(
        self: SoundDeviceBackend,
    ) -> list[AudioDevice]:
        return [device]

    def accept_capability(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        return None

    def reject_opening(
        self: SoundDeviceBackend,
        selected_device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        raise StreamOpenError(
            "Device is currently unavailable",
        )

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )
    monkeypatch.setattr(
        SoundDeviceBackend,
        "validate_stream_capability",
        accept_capability,
    )
    monkeypatch.setattr(
        SoundDeviceBackend,
        "validate_stream_opening",
        reject_opening,
    )

    result = runner.invoke(
        app,
        [
            "validate-stream",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 2
    assert "Device is currently unavailable" in result.stderr
