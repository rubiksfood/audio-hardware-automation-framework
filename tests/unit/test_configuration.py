from pathlib import Path

import pytest

from audio_hw_framework.configuration.loader import (
    ConfigurationError,
    load_config,
)


def test_load_config() -> None:
    config = load_config(Path("configs/example_duplex_device.yaml"))

    assert config.device.name_contains == "Scarlett"

    assert config.stream.sample_rate == 48000


def test_missing_config_file_raises() -> None:
    with pytest.raises(ConfigurationError):
        load_config(Path("does_not_exist.yaml"))


def test_empty_config_raises(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "empty.yaml"

    config_file.write_text(
        "",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError):
        load_config(config_file)


def test_invalid_yaml_raises(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "broken.yaml"

    config_file.write_text(
        "device: [",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError):
        load_config(config_file)


def test_load_config_with_audio_execution_settings(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.yaml"

    config_file.write_text(
        """
device:
  name_contains: "Scarlett"

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2

execution:
  duration_seconds: 2.5
  timeout_seconds: 10.0
  output_file: recordings/test.wav
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.execution.duration_seconds == 2.5
    assert config.execution.timeout_seconds == 10.0
    assert config.execution.output_file == Path("recordings/test.wav")
