from audio_hw_framework.backend.base import (
    AudioBackend,
    BackendInfo,
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.device.models import AudioDevice, StreamConfig

StreamKey = tuple[int, int, int, int, int | None, str]


class FakeAudioBackend(AudioBackend):
    """Deterministic backend used by hardware-independent tests."""

    def __init__(
        self,
        devices: list[AudioDevice] | None = None,
        unsupported_streams: set[StreamKey] | None = None,
        stream_open_failures: set[StreamKey] | None = None,
    ) -> None:
        self._devices = list(devices) if devices is not None else []
        self._unsupported_streams = (
            set(unsupported_streams) if unsupported_streams is not None else set()
        )
        self._stream_open_failures = (
            set(stream_open_failures) if stream_open_failures is not None else set()
        )

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
