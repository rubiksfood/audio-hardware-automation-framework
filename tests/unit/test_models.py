from audio_hw_framework.device.models import (
    AudioDevice,
    DeviceDirection,
)


def test_duplex_device_direction() -> None:
    device = AudioDevice(
        index=0,
        name="Scarlett",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    assert device.direction is DeviceDirection.DUPLEX


def test_input_device_direction() -> None:
    device = AudioDevice(
        index=0,
        name="Microphone",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    assert device.direction is DeviceDirection.INPUT


def test_output_device_direction() -> None:
    device = AudioDevice(
        index=0,
        name="Speakers",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=0,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    assert device.direction is DeviceDirection.OUTPUT


def test_device_with_no_channels_has_none_direction() -> None:
    device = AudioDevice(
        index=0,
        name="Unavailable Device",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=0,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    assert device.direction is DeviceDirection.NONE
