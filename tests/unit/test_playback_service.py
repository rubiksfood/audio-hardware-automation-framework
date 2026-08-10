import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import (
    AudioBackendError,
    StreamCapabilityError,
)
from audio_hw_framework.backend.fake_backend import FakeAudioBackend
from audio_hw_framework.device.matcher import (
    AmbiguousDeviceMatchError,
    DeviceNotFoundError,
)
from audio_hw_framework.device.models import (
    AudioDevice,
    AudioExecutionConfig,
    DeviceMatchConfig,
    FrameworkConfig,
    StreamConfig,
)
from audio_hw_framework.playback import (
    PlaybackExecutionError,
    play_configured_audio,
)


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


def create_config(
    *,
    sample_rate: int = 48_000,
    input_channels: int = 0,
    output_channels: int = 2,
    timeout_seconds: float = 5.0,
) -> FrameworkConfig:
    return FrameworkConfig(
        device=DeviceMatchConfig(
            name_contains="Scarlett",
            host_api_contains="WASAPI",
            minimum_output_channels=2,
        ),
        stream=StreamConfig(
            sample_rate=sample_rate,
            input_channels=input_channels,
            output_channels=output_channels,
            block_size=128,
        ),
        execution=AudioExecutionConfig(
            timeout_seconds=timeout_seconds,
        ),
    )


def create_audio(
    *,
    frame_count: int = 3,
    channel_count: int = 2,
    sample_rate: int = 48_000,
) -> AudioBuffer:
    return AudioBuffer(
        samples=np.zeros(
            (frame_count, channel_count),
            dtype=np.float32,
        ),
        sample_rate=sample_rate,
    )


class SpyPlaybackBackend(FakeAudioBackend):
    """Fake backend that records playback arguments for service tests."""

    def __init__(
        self,
        devices: list[AudioDevice],
    ) -> None:
        super().__init__(
            devices=devices,
        )

        self.playback_device: AudioDevice | None = None
        self.playback_config: StreamConfig | None = None
        self.playback_audio: AudioBuffer | None = None
        self.playback_timeout_seconds: float | None = None

    def playback(
        self,
        device: AudioDevice,
        config: StreamConfig,
        audio: AudioBuffer,
        *,
        timeout_seconds: float,
    ) -> None:
        self.playback_device = device
        self.playback_config = config
        self.playback_audio = audio
        self.playback_timeout_seconds = timeout_seconds

        super().playback(
            device,
            config,
            audio,
            timeout_seconds=timeout_seconds,
        )


def test_plays_audio_and_returns_result() -> None:
    device = create_device()
    backend = SpyPlaybackBackend(
        devices=[device],
    )
    config = create_config(
        timeout_seconds=7.5,
    )
    audio = create_audio()

    result = play_configured_audio(
        backend,
        config,
        audio,
    )

    assert result.backend == backend.info
    assert result.device == device
    assert result.stream == config.stream
    assert result.audio is audio

    assert backend.playback_device == device
    assert backend.playback_config == config.stream
    assert backend.playback_audio is audio
    assert backend.playback_timeout_seconds == 7.5


def test_plays_through_uniquely_matched_device() -> None:
    selected_device = create_device()

    unrelated_device = create_device(
        index=1,
        name="Built-in Audio",
    )

    backend = FakeAudioBackend(
        devices=[
            unrelated_device,
            selected_device,
        ],
    )

    result = play_configured_audio(
        backend,
        create_config(),
        create_audio(),
    )

    assert result.device == selected_device


def test_raises_when_no_device_matches() -> None:
    backend = FakeAudioBackend(
        devices=[
            create_device(
                name="Built-in Audio",
            ),
        ],
    )

    with pytest.raises(
        DeviceNotFoundError,
        match="No device matched configuration",
    ):
        play_configured_audio(
            backend,
            create_config(),
            create_audio(),
        )


def test_raises_when_device_match_is_ambiguous() -> None:
    backend = FakeAudioBackend(
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
        play_configured_audio(
            backend,
            create_config(),
            create_audio(),
        )


def test_rejects_playback_without_output_channels() -> None:
    backend = FakeAudioBackend(
        devices=[create_device()],
    )

    config = create_config(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        PlaybackExecutionError,
        match="requires at least one output channel",
    ):
        play_configured_audio(
            backend,
            config,
            create_audio(),
        )


def test_rejects_empty_audio_buffer() -> None:
    backend = FakeAudioBackend(
        devices=[create_device()],
    )

    audio = create_audio(
        frame_count=0,
    )

    with pytest.raises(
        PlaybackExecutionError,
        match="requires at least one audio frame",
    ):
        play_configured_audio(
            backend,
            create_config(),
            audio,
        )


def test_rejects_audio_sample_rate_mismatch() -> None:
    backend = FakeAudioBackend(
        devices=[create_device()],
    )

    audio = create_audio(
        sample_rate=44_100,
    )

    with pytest.raises(
        PlaybackExecutionError,
        match="sample rate",
    ):
        play_configured_audio(
            backend,
            create_config(
                sample_rate=48_000,
            ),
            audio,
        )


def test_rejects_audio_channel_count_mismatch() -> None:
    backend = FakeAudioBackend(
        devices=[create_device()],
    )

    audio = create_audio(
        channel_count=1,
    )

    with pytest.raises(
        PlaybackExecutionError,
        match="channel count",
    ):
        play_configured_audio(
            backend,
            create_config(
                output_channels=2,
            ),
            audio,
        )


def test_propagates_stream_capability_error() -> None:
    device = create_device()
    config = create_config()

    stream_key = (
        device.index,
        config.stream.sample_rate,
        config.stream.input_channels,
        config.stream.output_channels,
        config.stream.block_size,
        config.stream.dtype.value,
    )

    backend = FakeAudioBackend(
        devices=[device],
        unsupported_streams={
            stream_key,
        },
    )

    with pytest.raises(
        StreamCapabilityError,
        match="rejected stream configuration",
    ):
        play_configured_audio(
            backend,
            config,
            create_audio(),
        )


def test_propagates_backend_playback_error() -> None:
    device = create_device()
    config = create_config()

    playback_key = (
        device.index,
        config.stream.sample_rate,
        config.stream.output_channels,
        config.stream.dtype.value,
    )

    backend = FakeAudioBackend(
        devices=[device],
        playback_failures={
            playback_key,
        },
    )

    with pytest.raises(
        AudioBackendError,
        match="Fake backend playback failed",
    ):
        play_configured_audio(
            backend,
            config,
            create_audio(),
        )
