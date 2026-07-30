import pytest

from audio_hw_framework.backend.base import (
    AudioBackend,
    BackendInfo,
    DeviceEnumerationError,
    StreamCapabilityError,
    StreamOpenError,
)
from audio_hw_framework.device.matcher import (
    AmbiguousDeviceMatchError,
    DeviceNotFoundError,
)
from audio_hw_framework.device.models import (
    AudioDevice,
    DeviceMatchConfig,
    FrameworkConfig,
    StreamConfig,
)
from audio_hw_framework.validation.service import validate_configured_stream


class RecordingAudioBackend(AudioBackend):
    """Test backend that records validation workflow calls."""

    def __init__(
        self,
        devices: list[AudioDevice],
        *,
        enumeration_error: DeviceEnumerationError | None = None,
        capability_error: StreamCapabilityError | None = None,
        opening_error: StreamOpenError | None = None,
    ) -> None:
        self._devices = list(devices)
        self._enumeration_error = enumeration_error
        self._capability_error = capability_error
        self._opening_error = opening_error

        self.events: list[str] = []
        self.capability_device: AudioDevice | None = None
        self.capability_config: StreamConfig | None = None
        self.opening_device: AudioDevice | None = None
        self.opening_config: StreamConfig | None = None

    @property
    def info(self) -> BackendInfo:
        return BackendInfo(
            name="recording",
            library="internal",
            library_version=None,
        )

    def list_devices(self) -> list[AudioDevice]:
        self.events.append("list_devices")

        if self._enumeration_error is not None:
            raise self._enumeration_error

        return list(self._devices)

    def validate_stream_capability(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        self.events.append("validate_stream_capability")
        self.capability_device = device
        self.capability_config = config

        if self._capability_error is not None:
            raise self._capability_error

    def validate_stream_opening(
        self,
        device: AudioDevice,
        config: StreamConfig,
    ) -> None:
        self.events.append("validate_stream_opening")
        self.opening_device = device
        self.opening_config = config

        if self._opening_error is not None:
            raise self._opening_error


def create_device(
    *,
    index: int = 0,
    name: str = "Focusrite Scarlett 2i2 USB",
) -> AudioDevice:
    return AudioDevice(
        index=index,
        name=name,
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def create_config() -> FrameworkConfig:
    return FrameworkConfig(
        device=DeviceMatchConfig(
            name_contains="Scarlett",
            host_api_contains="WASAPI",
            minimum_input_channels=2,
            minimum_output_channels=2,
        ),
        stream=StreamConfig(
            sample_rate=48_000,
            input_channels=2,
            output_channels=2,
            block_size=128,
        ),
    )


def test_validates_selected_device_and_returns_result() -> None:
    selected_device = create_device()
    unrelated_device = create_device(
        index=1,
        name="Built-in Audio",
    )
    config = create_config()
    backend = RecordingAudioBackend(
        devices=[
            unrelated_device,
            selected_device,
        ]
    )

    result = validate_configured_stream(
        backend,
        config,
    )

    assert result.backend == backend.info
    assert result.device == selected_device
    assert result.stream == config.stream

    assert backend.capability_device == selected_device
    assert backend.capability_config == config.stream
    assert backend.opening_device == selected_device
    assert backend.opening_config == config.stream


def test_runs_validation_steps_in_order() -> None:
    backend = RecordingAudioBackend(
        devices=[create_device()],
    )

    validate_configured_stream(
        backend,
        create_config(),
    )

    assert backend.events == [
        "list_devices",
        "validate_stream_capability",
        "validate_stream_opening",
    ]


def test_propagates_device_enumeration_error() -> None:
    backend = RecordingAudioBackend(
        devices=[],
        enumeration_error=DeviceEnumerationError("Enumeration failed"),
    )

    with pytest.raises(
        DeviceEnumerationError,
        match="Enumeration failed",
    ):
        validate_configured_stream(
            backend,
            create_config(),
        )

    assert backend.events == ["list_devices"]


def test_raises_when_no_device_matches() -> None:
    backend = RecordingAudioBackend(
        devices=[
            create_device(
                name="Built-in Audio",
            )
        ],
    )

    with pytest.raises(
        DeviceNotFoundError,
        match="No device matched configuration",
    ):
        validate_configured_stream(
            backend,
            create_config(),
        )

    assert backend.events == ["list_devices"]


def test_raises_when_device_match_is_ambiguous() -> None:
    backend = RecordingAudioBackend(
        devices=[
            create_device(index=0),
            create_device(
                index=1,
                name="Focusrite Scarlett Solo USB",
            ),
        ],
    )

    with pytest.raises(
        AmbiguousDeviceMatchError,
        match="Multiple devices matched configuration",
    ):
        validate_configured_stream(
            backend,
            create_config(),
        )

    assert backend.events == ["list_devices"]


def test_stops_when_capability_validation_fails() -> None:
    backend = RecordingAudioBackend(
        devices=[create_device()],
        capability_error=StreamCapabilityError(
            "Unsupported stream configuration",
        ),
    )

    with pytest.raises(
        StreamCapabilityError,
        match="Unsupported stream configuration",
    ):
        validate_configured_stream(
            backend,
            create_config(),
        )

    assert backend.events == [
        "list_devices",
        "validate_stream_capability",
    ]


def test_propagates_stream_opening_error() -> None:
    backend = RecordingAudioBackend(
        devices=[create_device()],
        opening_error=StreamOpenError(
            "Could not open stream",
        ),
    )

    with pytest.raises(
        StreamOpenError,
        match="Could not open stream",
    ):
        validate_configured_stream(
            backend,
            create_config(),
        )

    assert backend.events == [
        "list_devices",
        "validate_stream_capability",
        "validate_stream_opening",
    ]
