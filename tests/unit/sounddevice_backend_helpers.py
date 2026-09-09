"""Shared helpers for sounddevice backend tests."""

from audio_hw_framework.device.models import (
    AudioDevice,
    DuplexEndpoints,
)


def create_test_device() -> AudioDevice:
    """Create the standard audio device used by sounddevice backend tests."""

    return AudioDevice(
        index=0,
        name="Scarlett",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def create_shared_test_endpoints() -> DuplexEndpoints:
    """Create shared duplex endpoints used by sounddevice backend tests."""

    device = create_test_device()

    return DuplexEndpoints(
        input_device=device,
        output_device=device,
    )


def create_split_test_endpoints() -> DuplexEndpoints:
    """Create separate duplex endpoints used by sounddevice backend tests."""

    input_device = AudioDevice(
        index=0,
        name="Scarlett Input",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=0,
        default_sample_rate=48_000,
    )

    output_device = AudioDevice(
        index=1,
        name="Scarlett Output",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=0,
        max_output_channels=2,
        default_sample_rate=48_000,
    )

    return DuplexEndpoints(
        input_device=input_device,
        output_device=output_device,
    )
