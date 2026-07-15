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
        default_sample_rate=48000,
    )

    assert device.direction is DeviceDirection.DUPLEX
