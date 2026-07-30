import json
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from audio_hw_framework.backend.base import (
    DeviceEnumerationError,
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.cli import app
from audio_hw_framework.device.models import AudioDevice, StreamConfig

runner = CliRunner()


def create_test_device() -> AudioDevice:
    return AudioDevice(
        index=0,
        name="Focusrite Scarlett 2i2 USB",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def write_test_config(
    path: Path,
    *,
    device_name: str = "Scarlett",
) -> None:
    path.write_text(
        f"""
device:
  name_contains: "{device_name}"
  host_api_contains: "WASAPI"
  minimum_input_channels: 2
  minimum_output_channels: 2

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2
  block_size: 128
  dtype: "float32"
""",
        encoding="utf-8",
    )


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Inspect and validate audio hardware" in result.stdout


def test_inspect_devices_displays_device(monkeypatch: MonkeyPatch) -> None:
    device = create_test_device()

    def fake_list_devices(self: SoundDeviceBackend) -> list[AudioDevice]:
        return [device]

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )

    result = runner.invoke(app, ["inspect-devices"])

    assert result.exit_code == 0
    assert "Focusrite" in result.stdout
    assert "WASAPI" in result.stdout
    assert "48000 Hz" in result.stdout


def test_inspect_devices_outputs_json(monkeypatch: MonkeyPatch) -> None:
    device = create_test_device()

    def fake_list_devices(self: SoundDeviceBackend) -> list[AudioDevice]:
        return [device]

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )

    result = runner.invoke(
        app,
        ["inspect-devices", "--json"],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["backend"]["name"] == "portaudio"
    assert len(payload["devices"]) == 1
    assert payload["devices"][0]["name"] == "Focusrite Scarlett 2i2 USB"
    assert payload["devices"][0]["matches_configuration"] is False


def test_inspect_devices_marks_config_match(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()

    def fake_list_devices(self: SoundDeviceBackend) -> list[AudioDevice]:
        return [device]

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
device:
  name_contains: "Scarlett"
  minimum_input_channels: 2
  minimum_output_channels: 2

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2
  block_size: null
  dtype: "float32"
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "inspect-devices",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert "*" in result.stdout
    assert "Matched 1 device(s)." in result.stdout


def test_inspect_devices_json_marks_config_match(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = create_test_device()

    def fake_list_devices(self: SoundDeviceBackend) -> list[AudioDevice]:
        return [device]

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
device:
  name_contains: "Scarlett"

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2
  block_size: null
  dtype: "float32"
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "inspect-devices",
            "--config",
            str(config_path),
            "--json",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["devices"][0]["matches_configuration"] is True


def test_inspect_devices_exits_when_no_devices(monkeypatch: MonkeyPatch) -> None:
    def fake_list_devices(self: SoundDeviceBackend) -> list[AudioDevice]:
        return []

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        fake_list_devices,
    )

    result = runner.invoke(app, ["inspect-devices"])

    assert result.exit_code == 1
    assert "No audio devices detected." in result.stdout


def test_inspect_devices_handles_backend_error(monkeypatch: MonkeyPatch) -> None:
    def raise_enumeration_error(self: SoundDeviceBackend) -> list[AudioDevice]:
        raise DeviceEnumerationError("PortAudio failure")

    monkeypatch.setattr(
        SoundDeviceBackend,
        "list_devices",
        raise_enumeration_error,
    )

    result = runner.invoke(app, ["inspect-devices"])

    assert result.exit_code == 2
    assert "PortAudio failure" in result.stderr


def test_inspect_devices_no_devices_table_output(
    monkeypatch: MonkeyPatch,
) -> None:
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
        ["inspect-devices"],
    )

    assert result.exit_code == 1
    assert "No audio devices detected." in result.stdout


def test_inspect_devices_no_devices_json_output(
    monkeypatch: MonkeyPatch,
) -> None:
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
        ["inspect-devices", "--json"],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["devices"] == []
    assert payload["backend"]["name"] == "portaudio"


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
        raise StreamCapabilityError("Unsupported sample rate")

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
        raise StreamOpenError("Device is currently unavailable")

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
