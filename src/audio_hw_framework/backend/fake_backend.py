from audio_hw_framework.backend.base import (
    AudioBackend,
    BackendInfo,
)
from audio_hw_framework.device.models import AudioDevice


class FakeAudioBackend(AudioBackend):
    def __init__(
        self,
        devices: list[AudioDevice] | None = None,
    ) -> None:
        self._devices = devices or []

    @property
    def info(self) -> BackendInfo:
        return BackendInfo(
            name="fake",
            library="internal",
            library_version=None,
        )

    def list_devices(self) -> list[AudioDevice]:
        return self._devices
