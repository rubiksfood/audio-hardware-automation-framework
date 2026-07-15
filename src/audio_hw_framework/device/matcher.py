from audio_hw_framework.device.models import (
    AudioDevice,
    DeviceMatchConfig,
)


class DeviceMatchError(Exception):
    """Base matching exception."""


class DeviceNotFoundError(DeviceMatchError):
    """No device matched."""


class AmbiguousDeviceMatchError(DeviceMatchError):
    """More than one device matched."""


def device_matches(
    device: AudioDevice,
    config: DeviceMatchConfig,
) -> bool:
    if config.exact_name and device.name.casefold() != config.exact_name.casefold():
        return False

    if config.name_contains and config.name_contains.casefold() not in device.name.casefold():
        return False

    if device.max_input_channels < config.minimum_input_channels:
        return False

    if device.max_output_channels < config.minimum_output_channels:
        return False

    return True


def find_matching_devices(
    devices: list[AudioDevice],
    config: DeviceMatchConfig,
) -> list[AudioDevice]:
    return [device for device in devices if device_matches(device, config)]


def find_unique_device(
    devices: list[AudioDevice],
    config: DeviceMatchConfig,
) -> AudioDevice:
    matches = find_matching_devices(
        devices,
        config,
    )

    if not matches:
        raise DeviceNotFoundError("No device matched configuration")

    if len(matches) > 1:
        raise AmbiguousDeviceMatchError("Multiple devices matched configuration")

    return matches[0]
