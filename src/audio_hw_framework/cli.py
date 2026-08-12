import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from audio_hw_framework.analysis import AudioAnalysisError
from audio_hw_framework.audio import WavFileError, read_wav
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.configuration.loader import (
    ConfigurationError,
    load_config,
)
from audio_hw_framework.device.matcher import (
    DeviceMatchError,
    find_matching_devices,
)
from audio_hw_framework.device.models import AudioDevice
from audio_hw_framework.playback import (
    PlaybackExecutionError,
    PlaybackResult,
    play_configured_audio,
)
from audio_hw_framework.recording import (
    RecordingExecutionError,
    RecordingResult,
    record_configured_audio,
)
from audio_hw_framework.validation import (
    AudioMetricValidationResult,
    StreamValidationResult,
    validate_audio_metrics,
    validate_configured_stream,
)

app = typer.Typer(
    no_args_is_help=True,
    help="Inspect and validate audio hardware.",
)

console = Console()
error_console = Console(stderr=True)


def build_device_table(
    devices: list[AudioDevice],
    matching_indexes: set[int],
) -> Table:
    table = Table(title="Detected audio devices")

    table.add_column("Match")
    table.add_column("Index", justify="right")
    table.add_column("Device")
    table.add_column("Host API")
    table.add_column("Inputs", justify="right")
    table.add_column("Outputs", justify="right")
    table.add_column("Default rate", justify="right")

    for device in devices:
        table.add_row(
            "*" if device.index in matching_indexes else "",
            str(device.index),
            device.name,
            device.host_api_name,
            str(device.max_input_channels),
            str(device.max_output_channels),
            f"{device.default_sample_rate:.0f} Hz",
        )

    return table


def build_stream_validation_table(
    result: StreamValidationResult,
) -> Table:
    """Build a human-readable stream validation summary."""

    block_size = (
        str(result.stream.block_size) if result.stream.block_size is not None else "automatic"
    )

    table = Table(title="Stream validation passed")

    table.add_column("Setting")
    table.add_column("Value")

    table.add_row("Backend", result.backend.name)
    table.add_row("Library", result.backend.library)
    table.add_row("Device", result.device.name)
    table.add_row("Device index", str(result.device.index))
    table.add_row("Host API", result.device.host_api_name)
    table.add_row("Sample rate", f"{result.stream.sample_rate} Hz")
    table.add_row("Input channels", str(result.stream.input_channels))
    table.add_row("Output channels", str(result.stream.output_channels))
    table.add_row("Block size", block_size)
    table.add_row("Data type", result.stream.dtype.value)

    return table


def build_recording_validation_table(
    result: RecordingResult,
) -> Table:
    """Build a human-readable recording validation summary."""

    table = Table(title="Recording validation passed")

    table.add_column("Setting")
    table.add_column("Value")

    table.add_row("Backend", result.backend.name)
    table.add_row("Device", result.device.name)
    table.add_row("Device index", str(result.device.index))
    table.add_row("Host API", result.device.host_api_name)
    table.add_row("Sample rate", f"{result.audio.sample_rate} Hz")
    table.add_row("Channels", str(result.audio.channel_count))
    table.add_row("Frames recorded", str(result.audio.frame_count))
    table.add_row(
        "Output file",
        str(result.output_file) if result.output_file is not None else "not exported",
    )

    return table


def build_playback_validation_table(
    result: PlaybackResult,
) -> Table:
    """Build a human-readable playback validation summary."""

    table = Table(title="Playback validation passed")

    table.add_column("Setting")
    table.add_column("Value")

    table.add_row("Backend", result.backend.name)
    table.add_row("Device", result.device.name)
    table.add_row("Device index", str(result.device.index))
    table.add_row("Host API", result.device.host_api_name)
    table.add_row("Sample rate", f"{result.audio.sample_rate} Hz")
    table.add_row("Channels", str(result.audio.channel_count))
    table.add_row("Frames played", str(result.audio.frame_count))

    return table


def build_audio_analysis_table(
    result: AudioMetricValidationResult,
) -> Table:
    """Build a human-readable sample-domain analysis summary."""

    title = "Audio analysis passed" if result.passed else "Audio analysis failed"

    table = Table(title=title)

    table.add_column("Metric")
    table.add_column("Overall")
    table.add_column("Per channel")

    table.add_row(
        "RMS",
        f"{result.rms.overall:.6f}",
        ", ".join(f"{value:.6f}" for value in result.rms.per_channel),
    )
    table.add_row(
        "Peak",
        f"{result.peak.overall:.6f}",
        ", ".join(f"{value:.6f}" for value in result.peak.per_channel),
    )
    table.add_row(
        "DC offset",
        f"{result.dc_offset.overall:.6f}",
        ", ".join(f"{value:.6f}" for value in result.dc_offset.per_channel),
    )
    table.add_row(
        "Silence detected",
        str(result.silence.detected),
        ", ".join(str(value) for value in result.silence.per_channel),
    )
    table.add_row(
        "Clipping detected",
        str(result.clipping.detected),
        ", ".join(str(value) for value in result.clipping.per_channel),
    )

    return table


def build_audio_analysis_failure_table(
    result: AudioMetricValidationResult,
) -> Table:
    """Build a human-readable summary of failed metric thresholds."""

    table = Table(title="Threshold failures")

    table.add_column("Metric")
    table.add_column("Channel", justify="right")
    table.add_column("Actual")
    table.add_column("Threshold")
    table.add_column("Reason")

    for failure in result.failures:
        table.add_row(
            failure.metric,
            str(failure.channel + 1),
            str(failure.actual),
            f"{failure.threshold:.6f}",
            failure.reason,
        )

    return table


@app.callback()
def main() -> None:
    """Inspect and validate audio hardware."""


@app.command("inspect-devices")
def inspect_devices(
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Optional YAML configuration file.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output device information as JSON.",
        ),
    ] = False,
) -> None:
    backend = SoundDeviceBackend()

    matches: list[AudioDevice] = []

    try:
        devices = backend.list_devices()

        if config_path is not None:
            config = load_config(config_path)
            matches = find_matching_devices(devices, config.device)

    except (AudioBackendError, ConfigurationError) as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    if json_output:
        payload = {
            "backend": {
                "name": backend.info.name,
                "library": backend.info.library,
                "library_version": backend.info.library_version,
            },
            "devices": [
                {
                    **device.model_dump(mode="json"),
                    "matches_configuration": device in matches,
                }
                for device in devices
            ],
        }

        typer.echo(json.dumps(payload, indent=2))
        return

    if not devices:
        console.print("[yellow]No audio devices detected.[/yellow]")
        raise typer.Exit(code=1)

    matching_indexes = {device.index for device in matches}

    console.print(
        build_device_table(
            devices,
            matching_indexes,
        )
    )

    if config_path is not None:
        console.print(f"\nMatched {len(matches)} device(s).")


@app.command("validate-stream")
def validate_stream(
    config_path: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="YAML configuration file to validate.",
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output validation results as JSON.",
        ),
    ] = False,
) -> None:
    """Validate a configured device and audio stream."""

    backend = SoundDeviceBackend()

    try:
        config = load_config(config_path)
        result = validate_configured_stream(
            backend,
            config,
        )

    except (
        AudioBackendError,
        ConfigurationError,
        DeviceMatchError,
    ) as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    if json_output:
        payload = {
            "status": "passed",
            "backend": {
                "name": result.backend.name,
                "library": result.backend.library,
                "library_version": result.backend.library_version,
            },
            "device": result.device.model_dump(mode="json"),
            "stream": result.stream.model_dump(mode="json"),
            "checks": {
                "capability": "passed",
                "stream_opening": "passed",
            },
        }

        typer.echo(json.dumps(payload, indent=2))
        return

    console.print(build_stream_validation_table(result))


@app.command("validate-recording")
def validate_recording(
    config_path: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="YAML configuration file for recording validation.",
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output recording validation results as JSON.",
        ),
    ] = False,
) -> None:
    """Execute and validate a finite configured recording."""

    backend = SoundDeviceBackend()

    try:
        config = load_config(config_path)
        result = record_configured_audio(
            backend,
            config,
        )

    except (
        AudioBackendError,
        ConfigurationError,
        DeviceMatchError,
        RecordingExecutionError,
        WavFileError,
    ) as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    if json_output:
        payload = {
            "status": "passed",
            "backend": {
                "name": result.backend.name,
                "library": result.backend.library,
                "library_version": result.backend.library_version,
            },
            "device": result.device.model_dump(mode="json"),
            "stream": result.stream.model_dump(mode="json"),
            "recording": {
                "sample_rate": result.audio.sample_rate,
                "channels": result.audio.channel_count,
                "frames": result.audio.frame_count,
                "output_file": (
                    str(result.output_file) if result.output_file is not None else None
                ),
            },
        }

        typer.echo(json.dumps(payload, indent=2))
        return

    console.print(
        build_recording_validation_table(result),
    )


@app.command("validate-playback")
def validate_playback(
    config_path: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="YAML configuration file for playback validation.",
        ),
    ],
    input_file: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="WAV file to use for playback validation.",
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output playback validation results as JSON.",
        ),
    ] = False,
) -> None:
    """Execute and validate finite playback from a WAV file."""

    backend = SoundDeviceBackend()

    try:
        config = load_config(config_path)
        audio = read_wav(input_file)

        result = play_configured_audio(
            backend,
            config,
            audio,
        )

    except (
        AudioBackendError,
        ConfigurationError,
        DeviceMatchError,
        PlaybackExecutionError,
        WavFileError,
    ) as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    if json_output:
        payload = {
            "status": "passed",
            "backend": {
                "name": result.backend.name,
                "library": result.backend.library,
                "library_version": result.backend.library_version,
            },
            "device": result.device.model_dump(mode="json"),
            "stream": result.stream.model_dump(mode="json"),
            "playback": {
                "input_file": str(input_file),
                "sample_rate": result.audio.sample_rate,
                "channels": result.audio.channel_count,
                "frames": result.audio.frame_count,
            },
        }

        typer.echo(json.dumps(payload, indent=2))
        return

    console.print(
        build_playback_validation_table(result),
    )


@app.command("analyse-audio")
def analyse_audio(
    config_path: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="YAML configuration file containing audio metric thresholds.",
        ),
    ],
    input_file: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="WAV file to analyse.",
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output audio analysis results as JSON.",
        ),
    ] = False,
) -> None:
    """Analyse a WAV file using configured sample-domain thresholds."""

    try:
        config = load_config(config_path)
        audio = read_wav(input_file)

        result = validate_audio_metrics(
            audio,
            config.thresholds,
        )

    except (
        AudioAnalysisError,
        ConfigurationError,
        WavFileError,
    ) as exc:
        error_console.print(
            f"[bold red]Error:[/bold red] {exc}",
        )
        raise typer.Exit(code=2) from exc

    if json_output:
        payload = {
            "status": ("passed" if result.passed else "failed"),
            "input_file": str(input_file),
            "audio": {
                "sample_rate": audio.sample_rate,
                "channels": audio.channel_count,
                "frames": audio.frame_count,
            },
            "metrics": {
                "rms": {
                    "overall": result.rms.overall,
                    "per_channel": result.rms.per_channel,
                },
                "peak": {
                    "overall": result.peak.overall,
                    "per_channel": result.peak.per_channel,
                },
                "dc_offset": {
                    "overall": result.dc_offset.overall,
                    "per_channel": result.dc_offset.per_channel,
                },
                "silence": {
                    "detected": result.silence.detected,
                    "per_channel": result.silence.per_channel,
                },
                "clipping": {
                    "detected": result.clipping.detected,
                    "per_channel": result.clipping.per_channel,
                },
            },
            "failures": [
                {
                    "metric": failure.metric,
                    "channel": failure.channel,
                    "actual": failure.actual,
                    "threshold": failure.threshold,
                    "reason": failure.reason,
                }
                for failure in result.failures
            ],
        }

        typer.echo(
            json.dumps(
                payload,
                indent=2,
            )
        )

    else:
        console.print(
            build_audio_analysis_table(result),
        )

        if result.failures:
            console.print()
            console.print(
                build_audio_analysis_failure_table(result),
            )

    if not result.passed:
        raise typer.Exit(code=1)
