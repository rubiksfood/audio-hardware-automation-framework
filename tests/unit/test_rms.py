import numpy as np
import pytest

from audio_hw_framework.analysis import (
    EmptyAudioBufferError,
    analyse_rms,
)
from audio_hw_framework.audio import AudioBuffer


def test_analyse_rms_returns_zero_for_silence() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_rms(audio)

    assert result.overall == pytest.approx(0.0)
    assert result.per_channel == pytest.approx((0.0,))


def test_analyse_rms_returns_one_for_full_scale_constant_signal() -> None:
    audio = AudioBuffer(
        samples=np.ones(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_rms(audio)

    assert result.overall == pytest.approx(1.0)
    assert result.per_channel == pytest.approx((1.0,))


def test_analyse_rms_handles_negative_samples() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [-1.0],
                [1.0],
                [-1.0],
                [1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_rms(audio)

    assert result.overall == pytest.approx(1.0)
    assert result.per_channel == pytest.approx((1.0,))


def test_analyse_rms_calculates_known_value() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0],
                [1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = analyse_rms(audio)

    expected = np.sqrt(0.5)

    assert result.overall == pytest.approx(expected)
    assert result.per_channel == pytest.approx((expected,))


def test_analyse_rms_calculates_per_channel_values() -> None:
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

    result = analyse_rms(audio)

    assert result.per_channel == pytest.approx((1.0, 0.0))


def test_analyse_rms_calculates_overall_value_across_channels() -> None:
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

    result = analyse_rms(audio)

    assert result.overall == pytest.approx(np.sqrt(0.5))


def test_analyse_rms_accepts_integer_samples_without_overflow() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [30_000],
                [-30_000],
            ],
            dtype=np.int16,
        ),
        sample_rate=48_000,
    )

    result = analyse_rms(audio)

    assert result.overall == pytest.approx(30_000.0)
    assert result.per_channel == pytest.approx((30_000.0,))


def test_analyse_rms_rejects_empty_audio_buffer() -> None:
    audio = AudioBuffer(
        samples=np.empty(
            (0, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        EmptyAudioBufferError,
        match="RMS analysis requires at least one audio frame",
    ):
        analyse_rms(audio)
