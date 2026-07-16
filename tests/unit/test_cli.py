import json
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from audio_hw_framework.backend.base import DeviceEnumerationError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.cli import app
from audio_hw_framework.device.models import AudioDevice

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
