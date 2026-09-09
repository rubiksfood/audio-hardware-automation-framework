"""Tests for the audio backend execution contract."""

import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import (
    AudioBackend,
    BackendInfo,
    BackendOperationNotSupportedError,
)
from audio_hw_framework.device.models import (
    AudioDevice,
    DuplexEndpoints,
    StreamConfig,
)


class UnsupportedAudioBackend(AudioBackend):
    """Minimal backend that does not implement optional audio execution."""

    @property
    def info(self) -> BackendInfo:
        return BackendInfo(
            name="unsupported",
            library="internal",
            library_version=None,
        )

    def list_devices(self) -> list[AudioDevice]:
        return []

    def validate_stream_capability(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        return None

    def validate_stream_opening(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        return None


def create_device() -> AudioDevice:
    """Create the duplex device used by backend contract tests."""

    return AudioDevice(
        index=0,
        name="Test Audio Device",
        host_api_index=0,
        host_api_name="Test API",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def create_endpoints() -> DuplexEndpoints:
    """Create duplex endpoints used by backend contract tests."""

    device = create_device()

    return DuplexEndpoints(
        input_device=device,
        output_device=device,
    )


def create_audio() -> AudioBuffer:
    """Create playback audio used by backend contract tests."""

    return AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )


def test_duplex_execution_is_unsupported_by_default() -> None:
    backend = UnsupportedAudioBackend()

    with pytest.raises(
        BackendOperationNotSupportedError,
        match="unsupported backend does not support duplex execution",
    ):
        backend.duplex(
            create_endpoints(),
            StreamConfig(
                sample_rate=48_000,
                input_channels=2,
                output_channels=2,
            ),
            create_audio(),
            timeout_seconds=5.0,
        )
