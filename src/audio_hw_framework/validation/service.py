"""Application service for configuration-driven stream validation."""

from dataclasses import dataclass

from audio_hw_framework.backend.base import AudioBackend, BackendInfo
from audio_hw_framework.device.matcher import find_unique_device
from audio_hw_framework.device.models import (
    AudioDevice,
    FrameworkConfig,
    StreamConfig,
)


@dataclass(frozen=True)
class StreamValidationResult:
    """Successful result of a configured stream validation."""

    backend: BackendInfo
    device: AudioDevice
    stream: StreamConfig


def validate_configured_stream(
    backend: AudioBackend,
    config: FrameworkConfig,
) -> StreamValidationResult:
    """Validate the configured device and stream using an audio backend."""

    devices = backend.list_devices()
    device = find_unique_device(devices, config.device)

    backend.validate_stream_capability(
        device,
        config.stream,
    )
    backend.validate_stream_opening(
        device,
        config.stream,
    )

    return StreamValidationResult(
        backend=backend.info,
        device=device,
        stream=config.stream,
    )
