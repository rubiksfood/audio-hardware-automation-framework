import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

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
from audio_hw_framework.validation import (
    StreamValidationResult,
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
