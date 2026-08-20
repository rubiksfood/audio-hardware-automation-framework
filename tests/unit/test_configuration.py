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


def test_load_config_with_audio_metric_thresholds(
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

thresholds:
  minimum_rms: 0.01
  maximum_rms: 0.8
  maximum_peak: 0.95
  maximum_abs_dc_offset: 0.02
  silence_threshold: 0.0001
  clipping_threshold: 1.0
  fail_on_silence: true
  fail_on_clipping: true
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.thresholds.minimum_rms == 0.01
    assert config.thresholds.maximum_rms == 0.8
    assert config.thresholds.maximum_peak == 0.95
    assert config.thresholds.maximum_abs_dc_offset == 0.02
    assert config.thresholds.silence_threshold == 0.0001
    assert config.thresholds.clipping_threshold == 1.0
    assert config.thresholds.fail_on_silence is True
    assert config.thresholds.fail_on_clipping is True


def test_load_loopback_configuration() -> None:
    config = load_config(
        Path("configs/example_loopback.yaml"),
    )

    assert config.loopback is not None

    assert config.loopback.output_channel == 0
    assert config.loopback.input_channel == 0
    assert config.loopback.signal_duration_seconds == 1.0
    assert config.loopback.frequency_hz == 1_000.0
    assert config.loopback.amplitude == 0.25
    assert config.loopback.frequency_tolerance_hz == 5.0
    assert config.loopback.padding_seconds == 0.1
