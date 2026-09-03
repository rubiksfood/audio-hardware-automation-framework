"""Shared helpers for fake audio backend tests."""

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.device.models import (
    AudioDevice,
    DuplexEndpoints,
    StreamConfig,
)


def create_test_device() -> AudioDevice:
    """Create the standard duplex device used by fake backend tests."""

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
    """Create shared duplex endpoints used by fake backend tests."""

    device = create_test_device()

    return DuplexEndpoints(
        input_device=device,
        output_device=device,
    )


def create_split_test_endpoints() -> DuplexEndpoints:
    """Create separate input and output endpoints for fake backend tests."""

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


def create_stream_key(
    device: AudioDevice,
    config: StreamConfig,
) -> tuple[int, int, int, int, int | None, str]:
    """Create a fake backend stream key."""

    return (
        device.index,
        config.sample_rate,
        config.input_channels,
        config.output_channels,
        config.block_size,
        config.dtype.value,
    )


def create_recording_key(
    device: AudioDevice,
    config: StreamConfig,
    frame_count: int,
) -> tuple[int, int, int, int, str]:
    """Create a fake backend recording key."""

    return (
        device.index,
        config.sample_rate,
        config.input_channels,
        frame_count,
        config.dtype.value,
    )


def create_playback_key(
    device: AudioDevice,
    config: StreamConfig,
) -> tuple[int, int, int, str]:
    """Create a fake backend playback key."""

    return (
        device.index,
        config.sample_rate,
        config.output_channels,
        config.dtype.value,
    )


def create_duplex_key(
    device: AudioDevice,
    config: StreamConfig,
    audio: AudioBuffer,
) -> tuple[int, int, int, int, int, str]:
    """Create a fake backend duplex key."""

    return (
        device.index,
        config.sample_rate,
        config.input_channels,
        config.output_channels,
        audio.frame_count,
        config.dtype.value,
    )
