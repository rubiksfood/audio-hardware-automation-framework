import pytest

from audio_hw_framework.device.matcher import (
    AmbiguousDeviceMatchError,
    DeviceNotFoundError,
    device_matches,
    find_matching_devices,
    find_unique_device,
)
from audio_hw_framework.device.models import (
    AudioDevice,
    DeviceMatchConfig,
)


def create_scarlett_device() -> AudioDevice:
    return AudioDevice(
        index=0,
        name="Focusrite Scarlett 2i2 USB",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def test_matches_name_contains() -> None:
    device = create_scarlett_device()

    assert device_matches(
        device,
        DeviceMatchConfig(name_contains="scarlett"),
    )


def test_matches_exact_name() -> None:
    device = create_scarlett_device()

    assert device_matches(
        device,
        DeviceMatchConfig(
            exact_name="Focusrite Scarlett 2i2 USB",
        ),
    )


def test_exact_name_case_insensitive() -> None:
    device = create_scarlett_device()

    assert device_matches(
        device,
        DeviceMatchConfig(
            exact_name="focusrite scarlett 2i2 usb",
        ),
    )


def test_exact_name_mismatch() -> None:
    device = create_scarlett_device()

    assert not device_matches(
        device,
        DeviceMatchConfig(
            exact_name="RME Babyface Pro FS",
        ),
    )


def test_name_contains_mismatch() -> None:
    device = create_scarlett_device()

    assert not device_matches(
        device,
        DeviceMatchConfig(
            name_contains="babyface",
        ),
    )


def test_rejects_insufficient_input_channels() -> None:
    device = AudioDevice(
        index=0,
        name="Microphone",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=1,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    assert not device_matches(
        device,
        DeviceMatchConfig(
            minimum_input_channels=2,
        ),
    )


def test_rejects_insufficient_output_channels() -> None:
    device = AudioDevice(
        index=0,
        name="Speaker",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=0,
        max_output_channels=1,
        default_sample_rate=48_000,
    )

    assert not device_matches(
        device,
        DeviceMatchConfig(
            minimum_output_channels=2,
        ),
    )


def test_find_matching_devices_returns_matches() -> None:
    scarlett = create_scarlett_device()

    microphone = AudioDevice(
        index=1,
        name="Built-in Microphone",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    matches = find_matching_devices(
        [scarlett, microphone],
        DeviceMatchConfig(name_contains="scarlett"),
    )

    assert matches == [scarlett]


def test_find_unique_device_returns_device() -> None:
    scarlett = create_scarlett_device()

    microphone = AudioDevice(
        index=1,
        name="Built-in Microphone",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    result = find_unique_device(
        [scarlett, microphone],
        DeviceMatchConfig(name_contains="scarlett"),
    )

    assert result == scarlett


def test_find_unique_device_raises_when_no_match() -> None:
    device = AudioDevice(
        index=0,
        name="Built-in Microphone",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    with pytest.raises(DeviceNotFoundError):
        find_unique_device(
            [device],
            DeviceMatchConfig(name_contains="scarlett"),
        )


def test_find_unique_device_raises_when_ambiguous() -> None:
    scarlett_1 = create_scarlett_device()

    scarlett_2 = AudioDevice(
        index=1,
        name="Focusrite Scarlett Solo USB",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    with pytest.raises(AmbiguousDeviceMatchError):
        find_unique_device(
            [scarlett_1, scarlett_2],
            DeviceMatchConfig(name_contains="scarlett"),
        )
