from abc import ABC, abstractmethod
from dataclasses import dataclass

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.device.models import AudioDevice, StreamConfig


@dataclass(frozen=True)
class BackendInfo:
    """Metadata describing an audio backend."""

    name: str
    library: str
    library_version: str | None


class AudioBackendError(Exception):
    """Base backend exception."""


class DeviceEnumerationError(AudioBackendError):
    """Device discovery failed."""


class StreamCapabilityError(AudioBackendError):
    """The requested stream configuration is not supported."""


class StreamOpenError(AudioBackendError):
    """The requested audio stream could not be opened."""


class BackendOperationNotSupportedError(AudioBackendError):
    """The backend does not yet support the requested audio operation."""


class AudioBackend(ABC):
    """Interface implemented by audio backend adapters."""

    @property
    @abstractmethod
    def info(self) -> BackendInfo:
        """Return backend metadata."""

    @abstractmethod
    def list_devices(self) -> list[AudioDevice]:
        """Return visible audio devices."""

    @abstractmethod
    def validate_stream_capability(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        """Validate whether a device supports the requested stream settings."""

    @abstractmethod
    def validate_stream_opening(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        """Open and close the requested stream to verify it can be created."""

    def record(
        self,
        device: AudioDevice,
        config: StreamConfig,
        *,
        frame_count: int,
        timeout_seconds: float,
    ) -> AudioBuffer:
        """Record a finite number of audio frames."""

        raise BackendOperationNotSupportedError(
            f"{self.info.name} backend does not support recording",
        )

    def playback(
        self,
        device: AudioDevice,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> None:
        """Play a finite framework-owned audio buffer."""

        raise BackendOperationNotSupportedError(
            f"{self.info.name} backend does not support playback",
        )
