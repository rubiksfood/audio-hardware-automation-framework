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
from audio_hw_framework.device.matcher import find_matching_devices
from audio_hw_framework.device.models import AudioDevice

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
