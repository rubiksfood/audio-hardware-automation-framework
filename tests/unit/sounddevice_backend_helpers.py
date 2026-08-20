"""Shared helpers for sounddevice backend tests."""

from audio_hw_framework.device.models import AudioDevice


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
