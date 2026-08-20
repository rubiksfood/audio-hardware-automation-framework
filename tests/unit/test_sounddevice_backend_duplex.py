"""Tests for PortAudio duplex execution."""

import time
from unittest.mock import Mock

import numpy as np
import pytest
import sounddevice as sd
from pytest import MonkeyPatch

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.device.models import AudioDevice, StreamConfig


def create_test_device() -> AudioDevice:
    """Create the duplex device used by PortAudio backend tests."""

    return AudioDevice(
        index=0,
        name="Scarlett",
        host_api_index=0,
        host_api_name="WASAPI",
        max_input_channels=2,
        max_output_channels=2,
        default_sample_rate=48_000,
    )


def create_playback_audio(
    *,
    frame_count: int = 4,
    channel_count: int = 2,
    sample_rate: int = 48_000,
) -> AudioBuffer:
    """Create playback audio used by PortAudio duplex tests."""

    return AudioBuffer(
        samples=np.zeros(
            (frame_count, channel_count),
            dtype=np.float32,
        ),
        sample_rate=sample_rate,
    )


def create_duplex_config(
    *,
    input_channels: int = 2,
    output_channels: int = 2,
    block_size: int | None = 128,
) -> StreamConfig:
    """Create the standard duplex stream configuration."""

    return StreamConfig(
        sample_rate=48_000,
        input_channels=input_channels,
        output_channels=output_channels,
        block_size=block_size,
    )


def test_duplex_executes_playback_and_capture(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    stream.write_available = 2
    stream.read_available = 2
    stream.write.return_value = False

    captured_samples = np.array(
        [
            [0.1, -0.1],
            [0.2, -0.2],
            [0.3, -0.3],
            [0.4, -0.4],
        ],
        dtype=np.float32,
    )

    stream.read.side_effect = [
        (
            captured_samples[:2],
            False,
        ),
        (
            captured_samples[2:],
            False,
        ),
    ]

    stream_factory = Mock(
        return_value=stream,
    )

    monkeypatch.setattr(
        sd,
        "Stream",
        stream_factory,
    )

    audio = create_playback_audio()

    result = SoundDeviceBackend().duplex(
        create_test_device(),
        create_duplex_config(),
        audio,
        timeout_seconds=5.0,
    )

    stream_factory.assert_called_once_with(
        samplerate=48_000,
        blocksize=128,
        device=(0, 0),
        channels=(2, 2),
        dtype=("float32", "float32"),
    )

    stream.start.assert_called_once_with()
    stream.stop.assert_called_once_with()
    stream.abort.assert_not_called()
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )

    assert stream.write.call_count == 2
    assert stream.read.call_count == 2

    assert result.sample_rate == 48_000
    assert result.frame_count == 4
    assert result.channel_count == 2

    np.testing.assert_array_equal(
        result.samples,
        captured_samples,
    )


def test_duplex_writes_complete_playback_buffer(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    stream.write_available = 2
    stream.read_available = 2
    stream.write.return_value = False

    stream.read.side_effect = [
        (
            np.zeros(
                (2, 2),
                dtype=np.float32,
            ),
            False,
        ),
        (
            np.zeros(
                (2, 2),
                dtype=np.float32,
            ),
            False,
        ),
    ]

    monkeypatch.setattr(
        sd,
        "Stream",
        Mock(return_value=stream),
    )

    playback_samples = np.array(
        [
            [0.1, -0.1],
            [0.2, -0.2],
            [0.3, -0.3],
            [0.4, -0.4],
        ],
        dtype=np.float32,
    )

    audio = AudioBuffer(
        samples=playback_samples,
        sample_rate=48_000,
    )

    SoundDeviceBackend().duplex(
        create_test_device(),
        create_duplex_config(),
        audio,
        timeout_seconds=5.0,
    )

    first_write = stream.write.call_args_list[0].args[0]
    second_write = stream.write.call_args_list[1].args[0]

    np.testing.assert_array_equal(
        first_write,
        playback_samples[:2],
    )
    np.testing.assert_array_equal(
        second_write,
        playback_samples[2:],
    )


def test_duplex_uses_automatic_block_size(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    stream.write_available = 4
    stream.read_available = 4
    stream.write.return_value = False
    stream.read.return_value = (
        np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        False,
    )

    stream_factory = Mock(
        return_value=stream,
    )

    monkeypatch.setattr(
        sd,
        "Stream",
        stream_factory,
    )

    SoundDeviceBackend().duplex(
        create_test_device(),
        create_duplex_config(
            block_size=None,
        ),
        create_playback_audio(),
        timeout_seconds=5.0,
    )

    assert stream_factory.call_args.kwargs["blocksize"] == 0


def test_duplex_returns_empty_capture_for_empty_playback(
    monkeypatch: MonkeyPatch,
) -> None:
    stream_factory = Mock()

    monkeypatch.setattr(
        sd,
        "Stream",
        stream_factory,
    )

    audio = create_playback_audio(
        frame_count=0,
    )

    result = SoundDeviceBackend().duplex(
        create_test_device(),
        create_duplex_config(),
        audio,
        timeout_seconds=5.0,
    )

    assert result.sample_rate == 48_000
    assert result.frame_count == 0
    assert result.channel_count == 2

    stream_factory.assert_not_called()


def test_duplex_rejects_zero_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="timeout_seconds must be greater than 0",
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(),
            create_playback_audio(),
            timeout_seconds=0.0,
        )


def test_duplex_rejects_negative_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="timeout_seconds must be greater than 0",
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(),
            create_playback_audio(),
            timeout_seconds=-1.0,
        )


def test_duplex_requires_input_channels() -> None:
    with pytest.raises(
        AudioBackendError,
        match="Cannot perform duplex execution with no input channels",
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(
                input_channels=0,
                output_channels=2,
            ),
            create_playback_audio(),
            timeout_seconds=5.0,
        )


def test_duplex_requires_output_channels() -> None:
    with pytest.raises(
        AudioBackendError,
        match="Cannot perform duplex execution with no output channels",
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(
                input_channels=2,
                output_channels=0,
            ),
            create_playback_audio(
                channel_count=1,
            ),
            timeout_seconds=5.0,
        )


def test_duplex_rejects_playback_sample_rate_mismatch() -> None:
    with pytest.raises(
        AudioBackendError,
        match=("Duplex playback audio sample rate does not match the stream sample rate"),
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(),
            create_playback_audio(
                sample_rate=44_100,
            ),
            timeout_seconds=5.0,
        )


def test_duplex_rejects_playback_channel_count_mismatch() -> None:
    with pytest.raises(
        AudioBackendError,
        match=("Duplex playback audio channel count does not match the stream output channels"),
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(),
            create_playback_audio(
                channel_count=1,
            ),
            timeout_seconds=5.0,
        )


def test_duplex_reports_output_underflow(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    stream.write_available = 4
    stream.read_available = 0
    stream.write.return_value = True

    monkeypatch.setattr(
        sd,
        "Stream",
        Mock(return_value=stream),
    )

    with pytest.raises(
        AudioBackendError,
        match="Output underflow during duplex execution",
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(),
            create_playback_audio(),
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_duplex_reports_input_overflow(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    stream.write_available = 4
    stream.read_available = 4
    stream.write.return_value = False

    stream.read.return_value = (
        np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        True,
    )

    monkeypatch.setattr(
        sd,
        "Stream",
        Mock(return_value=stream),
    )

    with pytest.raises(
        AudioBackendError,
        match="Input overflow during duplex execution",
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(),
            create_playback_audio(),
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_duplex_times_out_when_no_frames_are_available(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    stream.write_available = 0
    stream.read_available = 0

    monkeypatch.setattr(
        sd,
        "Stream",
        Mock(return_value=stream),
    )

    monotonic = Mock(
        side_effect=[
            0.0,
            6.0,
        ],
    )

    monkeypatch.setattr(
        time,
        "monotonic",
        monotonic,
    )

    with pytest.raises(
        AudioBackendError,
        match="Duplex execution timed out for device index 0",
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(),
            create_playback_audio(),
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_duplex_translates_portaudio_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def raise_portaudio_error(
        *args: object,
        **kwargs: object,
    ) -> None:
        raise sd.PortAudioError("failure")

    monkeypatch.setattr(
        sd,
        "Stream",
        raise_portaudio_error,
    )

    with pytest.raises(
        AudioBackendError,
        match="Could not perform duplex execution for device index 0",
    ):
        SoundDeviceBackend().duplex(
            create_test_device(),
            create_duplex_config(),
            create_playback_audio(),
            timeout_seconds=5.0,
        )
