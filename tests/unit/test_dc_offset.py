import numpy as np
import pytest

from audio_hw_framework.analysis import (
    EmptyAudioBufferError,
    analyse_dc_offset,
)
from audio_hw_framework.audio import AudioBuffer


def test_analyse_dc_offset_returns_zero_for_silence() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_dc_offset(audio)

    assert result.overall == pytest.approx(0.0)
    assert result.per_channel == pytest.approx((0.0,))


def test_analyse_dc_offset_returns_zero_for_centred_signal() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [-1.0],
                [1.0],
                [-0.5],
                [0.5],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_dc_offset(audio)

    assert result.overall == pytest.approx(0.0)
    assert result.per_channel == pytest.approx((0.0,))


def test_analyse_dc_offset_returns_positive_offset() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.25],
                [0.5],
                [0.75],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_dc_offset(audio)

    assert result.overall == pytest.approx(0.5)
    assert result.per_channel == pytest.approx((0.5,))


def test_analyse_dc_offset_returns_negative_offset() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [-0.25],
                [-0.5],
                [-0.75],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_dc_offset(audio)

    assert result.overall == pytest.approx(-0.5)
    assert result.per_channel == pytest.approx((-0.5,))


def test_analyse_dc_offset_calculates_per_channel_values() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.5, -0.5],
                [0.5, -0.5],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_dc_offset(audio)

    assert result.per_channel == pytest.approx((0.5, -0.5))


def test_analyse_dc_offset_calculates_overall_value_across_channels() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [1.0, 0.0],
                [1.0, 0.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_dc_offset(audio)

    assert result.overall == pytest.approx(0.5)


def test_analyse_dc_offset_accepts_integer_samples() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [10_000],
                [20_000],
            ],
            dtype=np.int16,
        ),
        sample_rate=48_000,
    )

    result = analyse_dc_offset(audio)

    assert result.overall == pytest.approx(15_000.0)
    assert result.per_channel == pytest.approx((15_000.0,))


def test_analyse_dc_offset_rejects_empty_audio_buffer() -> None:
    audio = AudioBuffer(
        samples=np.empty(
            (0, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        EmptyAudioBufferError,
        match="DC offset analysis requires at least one audio frame",
    ):
        analyse_dc_offset(audio)
