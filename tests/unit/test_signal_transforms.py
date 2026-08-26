"""Tests for audio signal transformations."""

import numpy as np
import pytest

from audio_hw_framework.audio import AudioBuffer
from audio_hw_framework.signal import (
    pad_signal,
    route_mono_signal,
)


def create_mono_audio() -> AudioBuffer:
    """Create a small deterministic mono test signal."""

    return AudioBuffer(
        samples=np.array(
            [
                [0.25],
                [-0.5],
                [0.75],
            ],
            dtype=np.float32,
        ),
        sample_rate=10,
    )


def test_route_mono_signal_routes_to_selected_output_channel() -> None:
    audio = create_mono_audio()

    result = route_mono_signal(
        audio,
        output_channel=1,
        output_channels=2,
    )

    expected = np.array(
        [
            [0.0, 0.25],
            [0.0, -0.5],
            [0.0, 0.75],
        ],
        dtype=np.float32,
    )

    assert result.sample_rate == audio.sample_rate
    assert result.frame_count == audio.frame_count
    assert result.channel_count == 2

    np.testing.assert_array_equal(
        result.samples,
        expected,
    )


def test_route_mono_signal_can_route_to_first_channel() -> None:
    audio = create_mono_audio()

    result = route_mono_signal(
        audio,
        output_channel=0,
        output_channels=2,
    )

    expected = np.array(
        [
            [0.25, 0.0],
            [-0.5, 0.0],
            [0.75, 0.0],
        ],
        dtype=np.float32,
    )

    np.testing.assert_array_equal(
        result.samples,
        expected,
    )


def test_route_mono_signal_supports_single_output_channel() -> None:
    audio = create_mono_audio()

    result = route_mono_signal(
        audio,
        output_channel=0,
        output_channels=1,
    )

    np.testing.assert_array_equal(
        result.samples,
        audio.samples,
    )


def test_route_mono_signal_preserves_dtype() -> None:
    audio = create_mono_audio()

    result = route_mono_signal(
        audio,
        output_channel=1,
        output_channels=2,
    )

    assert result.samples.dtype == audio.samples.dtype


def test_route_mono_signal_returns_framework_owned_buffer() -> None:
    audio = create_mono_audio()

    result = route_mono_signal(
        audio,
        output_channel=0,
        output_channels=1,
    )

    assert result is not audio
    assert not result.samples.flags.writeable


def test_route_mono_signal_rejects_multichannel_input() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        ValueError,
        match="Signal routing requires mono input audio",
    ):
        route_mono_signal(
            audio,
            output_channel=0,
            output_channels=2,
        )


def test_route_mono_signal_rejects_zero_output_channels() -> None:
    with pytest.raises(
        ValueError,
        match="output_channels must be greater than 0",
    ):
        route_mono_signal(
            create_mono_audio(),
            output_channel=0,
            output_channels=0,
        )


def test_route_mono_signal_rejects_negative_output_channel() -> None:
    with pytest.raises(
        ValueError,
        match="output_channel must be greater than or equal to 0",
    ):
        route_mono_signal(
            create_mono_audio(),
            output_channel=-1,
            output_channels=2,
        )


def test_route_mono_signal_rejects_out_of_range_output_channel() -> None:
    with pytest.raises(
        ValueError,
        match="output_channel must be less than output_channels",
    ):
        route_mono_signal(
            create_mono_audio(),
            output_channel=2,
            output_channels=2,
        )


def test_pad_signal_adds_silence_before_and_after_audio() -> None:
    audio = create_mono_audio()

    result = pad_signal(
        audio,
        padding_seconds=0.2,
    )

    expected = np.array(
        [
            [0.0],
            [0.0],
            [0.25],
            [-0.5],
            [0.75],
            [0.0],
            [0.0],
        ],
        dtype=np.float32,
    )

    assert result.sample_rate == audio.sample_rate
    assert result.frame_count == 7
    assert result.channel_count == 1

    np.testing.assert_array_equal(
        result.samples,
        expected,
    )


def test_pad_signal_preserves_multichannel_audio() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.25, 0.0],
                [-0.5, 0.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=10,
    )

    result = pad_signal(
        audio,
        padding_seconds=0.1,
    )

    expected = np.array(
        [
            [0.0, 0.0],
            [0.25, 0.0],
            [-0.5, 0.0],
            [0.0, 0.0],
        ],
        dtype=np.float32,
    )

    np.testing.assert_array_equal(
        result.samples,
        expected,
    )


def test_pad_signal_preserves_dtype() -> None:
    audio = create_mono_audio()

    result = pad_signal(
        audio,
        padding_seconds=0.2,
    )

    assert result.samples.dtype == audio.samples.dtype


def test_pad_signal_with_zero_padding_preserves_audio_content() -> None:
    audio = create_mono_audio()

    result = pad_signal(
        audio,
        padding_seconds=0.0,
    )

    assert result is not audio

    np.testing.assert_array_equal(
        result.samples,
        audio.samples,
    )


def test_pad_signal_rejects_negative_padding() -> None:
    with pytest.raises(
        ValueError,
        match="padding_seconds must be greater than or equal to 0",
    ):
        pad_signal(
            create_mono_audio(),
            padding_seconds=-0.1,
        )


def test_pad_signal_rejects_infinite_padding() -> None:
    with pytest.raises(
        ValueError,
        match="padding_seconds must be finite",
    ):
        pad_signal(
            create_mono_audio(),
            padding_seconds=float("inf"),
        )


def test_pad_signal_rejects_nan_padding() -> None:
    with pytest.raises(
        ValueError,
        match="padding_seconds must be finite",
    ):
        pad_signal(
            create_mono_audio(),
            padding_seconds=float("nan"),
        )


def test_routing_and_padding_compose_for_loopback_playback() -> None:
    audio = create_mono_audio()

    routed = route_mono_signal(
        audio,
        output_channel=1,
        output_channels=2,
    )

    result = pad_signal(
        routed,
        padding_seconds=0.1,
    )

    expected = np.array(
        [
            [0.0, 0.0],
            [0.0, 0.25],
            [0.0, -0.5],
            [0.0, 0.75],
            [0.0, 0.0],
        ],
        dtype=np.float32,
    )

    np.testing.assert_array_equal(
        result.samples,
        expected,
    )
