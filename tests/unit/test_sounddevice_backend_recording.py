"""Tests for sounddevice backend recording."""

import time
from unittest.mock import Mock, PropertyMock

import numpy as np
import pytest
import sounddevice as sd
from pytest import MonkeyPatch

from audio_hw_framework.backend.base import AudioBackendError
from audio_hw_framework.backend.sounddevice_backend import SoundDeviceBackend
from audio_hw_framework.device.models import SampleDType, StreamConfig
from tests.unit.sounddevice_backend_helpers import create_test_device


def test_records_requested_number_of_frames(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.read_available = 3
    stream.read.return_value = (
        np.array(
            [
                [0.1, -0.1],
                [0.2, -0.2],
                [0.3, -0.3],
            ],
            dtype=np.float32,
        ),
        False,
    )

    stream_factory = Mock(return_value=stream)

    monkeypatch.setattr(
        sd,
        "InputStream",
        stream_factory,
    )

    device = create_test_device()
    config = StreamConfig(
        sample_rate=48_000,
        input_channels=2,
        output_channels=0,
        block_size=128,
        dtype=SampleDType.FLOAT32,
    )

    result = SoundDeviceBackend().record(
        device,
        config,
        frame_count=3,
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
    stream.read.assert_called_once_with(3)
    stream.stop.assert_called_once_with()
    stream.abort.assert_not_called()
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )

    assert result.frame_count == 3
    assert result.channel_count == 2
    assert result.sample_rate == 48_000

    np.testing.assert_array_equal(
        result.samples,
        stream.read.return_value[0],
    )


def test_recording_accumulates_multiple_reads(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()

    type(stream).read_available = PropertyMock(
        side_effect=[2, 2],
    )

    stream.read.side_effect = [
        (
            np.zeros(
                (2, 2),
                dtype=np.float32,
            ),
            False,
        ),
        (
            np.ones(
                (1, 2),
                dtype=np.float32,
            ),
            False,
        ),
    ]

    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(return_value=stream),
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = SoundDeviceBackend().record(
        create_test_device(),
        config,
        frame_count=3,
        timeout_seconds=5.0,
    )

    assert result.frame_count == 3

    assert stream.read.call_args_list == [
        ((2,),),
        ((1,),),
    ]


def test_recording_rejects_stream_without_input_channels() -> None:
    config = StreamConfig(
        input_channels=0,
        output_channels=2,
    )

    with pytest.raises(
        AudioBackendError,
        match="no input channels",
    ):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_zero_frame_recording_returns_empty_buffer(
    monkeypatch: MonkeyPatch,
) -> None:
    stream_factory = Mock()

    monkeypatch.setattr(
        sd,
        "InputStream",
        stream_factory,
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    result = SoundDeviceBackend().record(
        create_test_device(),
        config,
        frame_count=0,
        timeout_seconds=5.0,
    )

    assert result.frame_count == 0
    assert result.channel_count == 2

    stream_factory.assert_not_called()


def test_recording_translates_stream_open_error(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(
            side_effect=sd.PortAudioError(
                "Device unavailable",
            ),
        ),
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="Could not record from device index 0",
    ):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )


def test_recording_closes_stream_after_portaudio_error(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.read_available = 3
    stream.read.side_effect = sd.PortAudioError(
        "Input failure",
    )

    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(return_value=stream),
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(AudioBackendError):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_recording_rejects_input_overflow(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.read_available = 3
    stream.read.return_value = (
        np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        True,
    )

    monkeypatch.setattr(
        sd,
        "InputStream",
        Mock(return_value=stream),
    )

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="Input overflow",
    ):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )

    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )


def test_recording_timeout_aborts_and_closes_stream(
    monkeypatch: MonkeyPatch,
) -> None:
    stream = Mock()
    stream.read_available = 0

    monkeypatch.setattr(
        sd,
        "InputStream",
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

    config = StreamConfig(
        input_channels=2,
        output_channels=0,
    )

    with pytest.raises(
        AudioBackendError,
        match="Recording timed out",
    ):
        SoundDeviceBackend().record(
            create_test_device(),
            config,
            frame_count=3,
            timeout_seconds=5.0,
        )

    stream.stop.assert_not_called()
    stream.abort.assert_called_once_with(
        ignore_errors=True,
    )
    stream.close.assert_called_once_with(
        ignore_errors=True,
    )
