"""Resolution of configured duplex input and output endpoints."""

from typing import Literal

from audio_hw_framework.device.matcher import (
    AmbiguousDeviceMatchError,
    DeviceMatchError,
    DeviceNotFoundError,
    find_matching_devices,
    find_unique_device,
)
from audio_hw_framework.device.models import (
    AudioDevice,
    DeviceMatchConfig,
    DuplexEndpoints,
    FrameworkConfig,
)

EndpointDirection = Literal["input", "output"]


class DuplexEndpointResolutionError(DeviceMatchError):
    """Duplex endpoint resolution failed."""


class DuplexEndpointCapabilityError(DuplexEndpointResolutionError):
    """A matched duplex endpoint lacks required channel capability."""


def resolve_duplex_endpoints(
    devices: list[AudioDevice],
    config: FrameworkConfig,
) -> DuplexEndpoints:
    """Resolve and validate configured devices for duplex execution."""

    if config.stream.input_channels == 0 or config.stream.output_channels == 0:
        raise DuplexEndpointResolutionError(
            "Duplex endpoint resolution requires a duplex stream",
        )

    if config.input_device is None and config.output_device is None:
        device = _resolve_shared_device(
            devices,
            config,
        )

        return DuplexEndpoints(
            input_device=device,
            output_device=device,
        )

    input_selector = config.input_device or config.device
    output_selector = config.output_device or config.device

    input_device = _resolve_directional_endpoint(
        devices,
        input_selector,
        direction="input",
        required_channels=config.stream.input_channels,
    )

    output_device = _resolve_directional_endpoint(
        devices,
        output_selector,
        direction="output",
        required_channels=config.stream.output_channels,
    )

    return DuplexEndpoints(
        input_device=input_device,
        output_device=output_device,
    )


def _resolve_shared_device(
    devices: list[AudioDevice],
    config: FrameworkConfig,
) -> AudioDevice:
    """Resolve the legacy single-device duplex configuration."""

    device = find_unique_device(
        devices,
        config.device,
    )

    _validate_endpoint_capability(
        device,
        direction="input",
        required_channels=config.stream.input_channels,
    )

    _validate_endpoint_capability(
        device,
        direction="output",
        required_channels=config.stream.output_channels,
    )

    return device


def _resolve_directional_endpoint(
    devices: list[AudioDevice],
    selector: DeviceMatchConfig,
    *,
    direction: EndpointDirection,
    required_channels: int,
) -> AudioDevice:
    """Resolve exactly one endpoint capable of the requested direction."""

    matches = find_matching_devices(
        devices,
        selector,
    )

    if not matches:
        raise DeviceNotFoundError(
            f"No {direction} device matched configuration",
        )

    capable_matches = [
        device
        for device in matches
        if _available_channels(
            device,
            direction,
        )
        >= required_channels
    ]

    if not capable_matches:
        if len(matches) == 1:
            _validate_endpoint_capability(
                matches[0],
                direction=direction,
                required_channels=required_channels,
            )

        raise DuplexEndpointCapabilityError(
            f"No matched {direction} device provides the required "
            f"{required_channels} {direction} channels",
        )

    if len(capable_matches) > 1:
        raise AmbiguousDeviceMatchError(
            f"Multiple {direction} devices matched configuration",
        )

    return capable_matches[0]


def _validate_endpoint_capability(
    device: AudioDevice,
    *,
    direction: EndpointDirection,
    required_channels: int,
) -> None:
    """Require an endpoint to expose enough channels for one direction."""

    available_channels = _available_channels(
        device,
        direction,
    )

    if available_channels < required_channels:
        raise DuplexEndpointCapabilityError(
            f"{direction.capitalize()} device '{device.name}' provides "
            f"{available_channels} {direction} channels; "
            f"{required_channels} required",
        )


def _available_channels(
    device: AudioDevice,
    direction: EndpointDirection,
) -> int:
    """Return the channel capability for one endpoint direction."""

    if direction == "input":
        return device.max_input_channels

    return device.max_output_channels
