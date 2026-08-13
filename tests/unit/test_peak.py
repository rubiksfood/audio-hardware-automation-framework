import numpy as np
import pytest

from audio_hw_framework.analysis import (
    EmptyAudioBufferError,
    analyse_peak,
)
from audio_hw_framework.audio import AudioBuffer


def test_analyse_peak_returns_zero_for_silence() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_peak(audio)

    assert result.overall == pytest.approx(0.0)
    assert result.per_channel == pytest.approx((0.0,))


def test_analyse_peak_returns_positive_peak() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.1],
                [0.5],
                [0.25],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_peak(audio)

    assert result.overall == pytest.approx(0.5)
    assert result.per_channel == pytest.approx((0.5,))


def test_analyse_peak_uses_absolute_sample_magnitude() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.5],
                [-0.75],
                [0.25],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_peak(audio)

    assert result.overall == pytest.approx(0.75)
    assert result.per_channel == pytest.approx((0.75,))


def test_analyse_peak_calculates_per_channel_values() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.25, -0.5],
                [-0.75, 0.25],
                [0.5, 1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_peak(audio)

    assert result.per_channel == pytest.approx((0.75, 1.0))


def test_analyse_peak_calculates_overall_value_across_channels() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.25, -0.5],
                [-0.75, 0.25],
                [0.5, 1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_peak(audio)

    assert result.overall == pytest.approx(1.0)


def test_analyse_peak_handles_minimum_int16_value() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [-32_768],
                [10_000],
            ],
            dtype=np.int16,
        ),
        sample_rate=48_000,
    )

    result = analyse_peak(audio)

    assert result.overall == pytest.approx(32_768.0)
    assert result.per_channel == pytest.approx((32_768.0,))


def test_analyse_peak_rejects_empty_audio_buffer() -> None:
    audio = AudioBuffer(
        samples=np.empty(
            (0, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        EmptyAudioBufferError,
        match="Peak analysis requires at least one audio frame",
    ):
        analyse_peak(audio)
