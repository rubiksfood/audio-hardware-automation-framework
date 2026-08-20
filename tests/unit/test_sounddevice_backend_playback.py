"""Tests for sounddevice backend playback."""

import time
from unittest.mock import Mock, PropertyMock

import numpy as np
import pytest
import sounddevice as sd
from pytest import MonkeyPatch

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.device.models import StreamConfig
from tests.unit.sounddevice_backend_helpers import create_test_device


def test_plays_audio_buffer(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.write_available = 3
    stream.write.return_value = False

    stream_factory = Mock(return_value=stream)

    monkeypatch.setattr(
        sd,
        "OutputStream",
        stream_factory,
    )

    audio = AudioBuffer(
        samples=np.array(
            [
                [0.1, -0.1],
                [0.2, -0.2],
                [0.3, -0.3],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        sample_rate=48_000,
        input_channels=0,
        output_channels=2,
        block_size=128,
    )

    SoundDeviceBackend().playback(
        create_test_device(),
        config,
        audio,
        timeout_seconds=5.0,
    )

    stream_factory.assert_called_once_with(
        samplerate=48_000,
        blocksize=128,
        device=0,
        channels=2,
        dtype="float32",
    )

    stream.start.assert_called_once_with()
    stream.write.assert_called_once()
    stream.stop.assert_called_once_with()
    stream.abort.assert_not_called()
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )

    written = stream.write.call_args.args[0]

    np.testing.assert_array_equal(
        written,
        audio.samples,
    )


def test_playback_writes_multiple_chunks(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    type(stream).write_available = PropertyMock(
        side_effect=[2, 2],
    )

    stream.write.return_value = False

    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(return_value=stream),
    )

    audio = AudioBuffer(
        samples=np.array(
            [
                [0.1, -0.1],
                [0.2, -0.2],
                [0.3, -0.3],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    SoundDeviceBackend().playback(
        create_test_device(),
        config,
        audio,
        timeout_seconds=5.0,
    )

    assert stream.write.call_count == 2

    first_chunk = stream.write.call_args_list[0].args[0]
    second_chunk = stream.write.call_args_list[1].args[0]

    np.testing.assert_array_equal(
        first_chunk,
        audio.samples[:2],
    )
    np.testing.assert_array_equal(
        second_chunk,
        audio.samples[2:],
    )


def test_playback_rejects_stream_without_output_channels() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="no output channels",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_playback_rejects_sample_rate_mismatch() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=44_100,
    )

    config = StreamConfig(
        sample_rate=48_000,
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="sample rate",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_playback_rejects_channel_mismatch() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="channel count",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_zero_frame_playback_does_not_open_stream(
    monkeypatch: MonkeyPatch,
) -> None:
    stream_factory = Mock()

    monkeypatch.setattr(
        sd,
        "OutputStream",
        stream_factory,
    )

    audio = AudioBuffer(
        samples=np.empty(
            (0, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    SoundDeviceBackend().playback(
        create_test_device(),
        config,
        audio,
        timeout_seconds=5.0,
    )

    stream_factory.assert_not_called()


def test_playback_translates_stream_open_error(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(
            side_effect=sd.PortAudioError(
                "Device unavailable",
            ),
        ),
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="Could not play through device index 0",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )


def test_playback_aborts_and_closes_after_portaudio_error(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.write_available = 3
    stream.write.side_effect = sd.PortAudioError(
        "Output failure",
    )

    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(return_value=stream),
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(AudioBackendError):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_playback_rejects_output_underflow(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.write_available = 3
    stream.write.return_value = True

    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(return_value=stream),
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="Output underflow",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )

    stream.stop.assert_not_called()
    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_playback_timeout_aborts_and_closes_stream(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.write_available = 0

    monkeypatch.setattr(
        sd,
        "OutputStream",
        Mock(return_value=stream),
    )

    times = iter((
        0.0,
        0.0,
        6.0,
    ))

    monkeypatch.setattr(
        time,
        "monotonic",
        lambda: next(times),
    )
    monkeypatch.setattr(
        time,
        "sleep",
        lambda _: None,
    )

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="Playback timed out",
    ):
        SoundDeviceBackend().playback(
            create_test_device(),
            config,
            audio,
            timeout_seconds=5.0,
        )

    stream.write.assert_not_called()
    stream.stop.assert_not_called()
    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )
