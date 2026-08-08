"""Application service for configuration-driven audio recording."""

from dataclasses import dataclass
from pathlib import Path

from audio_hw_framework.audio import AudioBuffer, write_wav
from audio_hw_framework.backend.base import AudioBackend, BackendInfo
from audio_hw_framework.device.matcher import find_unique_device
from audio_hw_framework.device.models import (
    AudioDevice,
    FrameworkConfig,
    StreamConfig,
)


class RecordingExecutionError(RuntimeError):
    """Recording execution could not satisfy the framework contract."""


@dataclass(frozen=True)
class RecordingResult:
    """Successful result of a configured recording execution."""

    backend: BackendInfo
    device: AudioDevice
    stream: StreamConfig
    audio: AudioBuffer
    output_file: Path | None


def record_configured_audio(
    backend: AudioBackend,
    config: FrameworkConfig,
) -> RecordingResult:
    """Record audio using the configured device and execution settings."""

    if config.stream.input_channels == 0:
        raise RecordingExecutionError(
            "Recording requires at least one input channel",
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

    frame_count = round(config.execution.duration_seconds * config.stream.sample_rate)

    if frame_count <= 0:
        raise RecordingExecutionError(
            "Configured recording duration produces no audio frames",
        )

    audio = backend.record(
        device,
        config.stream,
        frame_count=frame_count,
        timeout_seconds=config.execution.timeout_seconds,
    )

    _validate_recording_result(
        audio,
        config.stream,
        frame_count,
    )

    output_file = config.execution.output_file

    if output_file is not None:
        write_wav(
            output_file,
            audio,
        )

    return RecordingResult(
        backend=backend.info,
        device=device,
        stream=config.stream,
        audio=audio,
        output_file=output_file,
    )


def _validate_recording_result(
    audio: AudioBuffer,
    stream: StreamConfig,
    expected_frame_count: int,
) -> None:
    """Verify that a backend satisfied the recording contract."""

    if audio.frame_count != expected_frame_count:
        raise RecordingExecutionError(
            "Backend returned an unexpected number of recording frames: "
            f"expected {expected_frame_count}, received {audio.frame_count}",
        )

    if audio.sample_rate != stream.sample_rate:
        raise RecordingExecutionError(
            "Backend returned audio with an unexpected sample rate",
        )

    if audio.channel_count != stream.input_channels:
        raise RecordingExecutionError(
            "Backend returned audio with an unexpected channel count",
        )
