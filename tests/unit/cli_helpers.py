"""Shared helpers for CLI unit tests."""

from pathlib import Path

from typer.testing import CliRunner

from audio_hw_framework.device.models import AudioDevice

runner = CliRunner()


def create_test_device() -> AudioDevice:
    """Create the standard audio device used by CLI tests."""

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
    """Write a duplex stream configuration for CLI tests."""

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


def write_recording_config(
    path: Path,
    *,
    output_file: Path | None = None,
) -> None:
    """Write an input-only recording configuration for CLI tests."""

    output_value = f'"{output_file.as_posix()}"' if output_file is not None else "null"

    path.write_text(
        f"""
device:
  name_contains: "Scarlett"
  host_api_contains: "WASAPI"
  minimum_input_channels: 2

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 0
  block_size: 128
  dtype: "float32"

execution:
  duration_seconds: 0.001
  timeout_seconds: 5.0
  output_file: {output_value}
""",
        encoding="utf-8",
    )


def write_playback_config(
    path: Path,
) -> None:
    """Write an output-only playback configuration for CLI tests."""

    path.write_text(
        """
device:
  name_contains: "Scarlett"
  host_api_contains: "WASAPI"
  minimum_output_channels: 2

stream:
  sample_rate: 48000
  input_channels: 0
  output_channels: 2
  block_size: 128
  dtype: "float32"

execution:
  timeout_seconds: 5.0
""",
        encoding="utf-8",
    )


def write_analysis_config(
    path: Path,
    *,
    minimum_rms: float | None = None,
    maximum_peak: float | None = None,
    fail_on_silence: bool = True,
) -> None:
    """Write a sample-domain analysis configuration for CLI tests."""

    minimum_rms_value = str(minimum_rms) if minimum_rms is not None else "null"
    maximum_peak_value = str(maximum_peak) if maximum_peak is not None else "null"

    path.write_text(
        f"""
device:
  name_contains: "Scarlett"

stream:
  sample_rate: 48000
  input_channels: 2
  output_channels: 2

thresholds:
  minimum_rms: {minimum_rms_value}
  maximum_peak: {maximum_peak_value}
  fail_on_silence: {str(fail_on_silence).lower()}
""",
        encoding="utf-8",
    )
