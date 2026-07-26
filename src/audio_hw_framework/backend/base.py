from abc import ABC, abstractmethod
from dataclasses import dataclass

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
