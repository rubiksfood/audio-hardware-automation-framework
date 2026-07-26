from audio_hw_framework.backend.base import (
    AudioBackend,
    BackendInfo,
    StreamCapabilityError,
)
from audio_hw_framework.device.models import AudioDevice, StreamConfig


class FakeAudioBackend(AudioBackend):
    """Deterministic backend used by hardware-independent tests."""

    def __init__(
        self,
        devices: list[AudioDevice] | None = None,
        unsupported_streams: set[tuple[int, int, int]] | None = None,
    ) -> None:
        self._devices = list(devices) if devices is not None else []
        self._unsupported_streams = (
            set(unsupported_streams) if unsupported_streams is not None else set()
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
        stream_key = (
            device.index,
            config.input_channels,
            config.output_channels,
        )

        if stream_key in self._unsupported_streams:
            raise StreamCapabilityError(
                f"Fake backend rejected stream configuration for device index {device.index}"
            )
