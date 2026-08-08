"""Application service for configuration-driven audio playback."""

from dataclasses import dataclass

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import AudioBackend, BackendInfo
from audio_hw_framework.device.matcher import find_unique_device
from audio_hw_framework.device.models import (
    AudioDevice,
    FrameworkConfig,
    StreamConfig,
)


class PlaybackExecutionError(RuntimeError):
    """Playback execution could not satisfy the framework contract."""


@dataclass(frozen=True)
class PlaybackResult:
    """Successful result of a configured playback execution."""

    backend: BackendInfo
    device: AudioDevice
    stream: StreamConfig
    audio: AudioBuffer


def play_configured_audio(
    backend: AudioBackend,
    config: FrameworkConfig,
    audio: AudioBuffer,
) -> PlaybackResult:
    """Play audio using the configured device and execution settings."""

    _validate_playback_request(
        audio,
        config.stream,
    )

    devices = backend.list_devices()
    device = find_unique_device(
        devices,
        config.device,
    )

    backend.validate_stream_capability(
        device,
        config.stream,
    )

    backend.playback(
        device,
        config.stream,
        audio,
        timeout_seconds=config.execution.timeout_seconds,
    )

    return PlaybackResult(
        backend=backend.info,
        device=device,
        stream=config.stream,
        audio=audio,
    )


def _validate_playback_request(
    audio: AudioBuffer,
    stream: StreamConfig,
) -> None:
    """Verify that audio is compatible with the configured output stream."""

    if stream.output_channels == 0:
        raise PlaybackExecutionError(
            "Playback requires at least one output channel",
        )

    if audio.frame_count == 0:
        raise PlaybackExecutionError(
            "Playback requires at least one audio frame",
        )

    if audio.sample_rate != stream.sample_rate:
        raise PlaybackExecutionError(
            "Playback audio sample rate does not match the configured stream",
        )

    if audio.channel_count != stream.output_channels:
        raise PlaybackExecutionError(
            "Playback audio channel count does not match the configured stream",
        )
