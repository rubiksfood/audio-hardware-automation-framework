import numpy as np

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import (
    AudioBackend,
    AudioBackendError,
    BackendInfo,
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.device.models import AudioDevice, StreamConfig

StreamKey = tuple[int, int, int, int, int | None, str]
RecordingKey = tuple[int, int, int, int, str]
PlaybackKey = tuple[int, int, int, str]


class FakeAudioBackend(AudioBackend):
    """Deterministic backend used by hardware-independent tests."""

    def __init__(
        self,
        devices: list[AudioDevice] | None = None,
        unsupported_streams: set[StreamKey] | None = None,
        stream_open_failures: set[StreamKey] | None = None,
        recording_samples: AudioBuffer | None = None,
        recording_failures: set[RecordingKey] | None = None,
        playback_failures: set[PlaybackKey] | None = None,
    ) -> None:
        self._devices = list(devices) if devices is not None else []

        self._unsupported_streams = (
            set(unsupported_streams) if unsupported_streams is not None else set()
        )

        self._stream_open_failures = (
            set(stream_open_failures) if stream_open_failures is not None else set()
        )

        self._recording_samples = recording_samples

        self._recording_failures = (
            set(recording_failures) if recording_failures is not None else set()
        )

        self._playback_failures = set(playback_failures) if playback_failures is not None else set()

    @property
    def info(self) -> BackendInfo:
        return BackendInfo(
            name="fake",
            library="internal",
            library_version=None,
        )

    def list_devices(self) -> list[AudioDevice]:
        return list(self._devices)

    def validate_stream_capability(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        stream_key = self._create_stream_key(device, config)

        if stream_key in self._unsupported_streams:
            raise StreamCapabilityError(
                f"Fake backend rejected stream configuration for device index {device.index}"
            )

    def validate_stream_opening(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        stream_key = self._create_stream_key(device, config)

        if stream_key in self._stream_open_failures:
            raise StreamOpenError(
                f"Fake backend could not open stream for device index {device.index}"
            )

    def record(
        self,
        device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        if frame_count < 0:
            raise ValueError("frame_count must be greater than or equal to 0")

        recording_key = self._create_recording_key(
            device,
            config,
            frame_count,
        )

        if recording_key in self._recording_failures:
            raise AudioBackendError(
                f"Fake backend recording failed for device index {device.index}",
            )

        if config.input_channels == 0:
            raise AudioBackendError(
                "Cannot record from a stream with no input channels",
            )

        if self._recording_samples is None:
            samples = np.zeros(
                (frame_count, config.input_channels),
                dtype=config.dtype.value,
            )

            return AudioBuffer(
                samples=samples,
                sample_rate=config.sample_rate,
            )

        if self._recording_samples.sample_rate != config.sample_rate:
            raise AudioBackendError(
                "Configured recording samples do not match the stream sample rate",
            )

        if self._recording_samples.channel_count != config.input_channels:
            raise AudioBackendError(
                "Configured recording samples do not match the stream input channels",
            )

        if self._recording_samples.frame_count < frame_count:
            raise AudioBackendError(
                "Configured recording samples contain fewer frames than requested",
            )

        return AudioBuffer(
            samples=self._recording_samples.samples[:frame_count],
            sample_rate=self._recording_samples.sample_rate,
        )

    def playback(
        self,
        device: AudioDevice,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> None:
        playback_key = self._create_playback_key(
            device,
            config,
        )

        if playback_key in self._playback_failures:
            raise AudioBackendError(
                f"Fake backend playback failed for device index {device.index}",
            )

        if config.output_channels == 0:
            raise AudioBackendError(
                "Cannot play audio through a stream with no output channels",
            )

        if audio.sample_rate != config.sample_rate:
            raise AudioBackendError(
                "Playback audio sample rate does not match the stream sample rate",
            )

        if audio.channel_count != config.output_channels:
            raise AudioBackendError(
                "Playback audio channel count does not match the stream output channels",
            )

    @staticmethod
    def _create_stream_key(
        device: AudioDevice,
        config: StreamConfig,
    ) -> StreamKey:
        return (
            device.index,
            config.sample_rate,
            config.input_channels,
            config.output_channels,
            config.block_size,
            config.dtype.value,
        )

    @staticmethod
    def _create_recording_key(
        device: AudioDevice,
        config: StreamConfig,
        frame_count: int,
    ) -> RecordingKey:
        return (
            device.index,
            config.sample_rate,
            config.input_channels,
            frame_count,
            config.dtype.value,
        )

    @staticmethod
    def _create_playback_key(
        device: AudioDevice,
        config: StreamConfig,
    ) -> PlaybackKey:
        return (
            device.index,
            config.sample_rate,
            config.output_channels,
            config.dtype.value,
        )
