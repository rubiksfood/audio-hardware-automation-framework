from abc import ABC, abstractmethod
from dataclasses import dataclass

from audio_hw_framework.device.models import AudioDevice


@dataclass(frozen=True)
class BackendInfo:
    name: str
    library: str
    library_version: str | None


class AudioBackendError(Exception):
    """Base backend exception."""


class DeviceEnumerationError(AudioBackendError):
    """Device discovery failed."""


class AudioBackend(ABC):
    @property
    @abstractmethod
    def info(self) -> BackendInfo:
        """Return backend metadata."""

    @abstractmethod
    def list_devices(self) -> list[AudioDevice]:
        """Return visible audio devices."""
