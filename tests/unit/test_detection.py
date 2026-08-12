import numpy as np
import pytest

from audio_hw_framework.analysis import (
    EmptyAudioBufferError,
    detect_clipping,
    detect_silence,
)
from audio_hw_framework.audio import AudioBuffer


def test_detect_silence_returns_true_for_zero_signal() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_silence(audio)

    assert result.detected is True
    assert result.per_channel == (True,)


def test_detect_silence_accepts_samples_at_threshold() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0001],
                [-0.0001],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_silence(
        audio,
        threshold=0.0001,
    )

    assert result.detected is True
    assert result.per_channel == (True,)


def test_detect_silence_returns_false_above_threshold() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0],
                [0.001],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_silence(
        audio,
        threshold=0.0001,
    )

    assert result.detected is False
    assert result.per_channel == (False,)


def test_detect_silence_reports_per_channel_values() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0, 0.0],
                [0.0, 0.5],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_silence(
        audio,
        threshold=0.0001,
    )

    assert result.detected is False
    assert result.per_channel == (
        True,
        False,
    )


def test_detect_silence_rejects_negative_threshold() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (1, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        ValueError,
        match="Silence threshold must be greater than or equal to 0",
    ):
        detect_silence(
            audio,
            threshold=-0.1,
        )


def test_detect_silence_rejects_empty_audio_buffer() -> None:
    audio = AudioBuffer(
        samples=np.empty(
            (0, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        EmptyAudioBufferError,
        match="Silence detection requires at least one audio frame",
    ):
        detect_silence(audio)


def test_detect_clipping_returns_false_below_threshold() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.5],
                [-0.75],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_clipping(audio)

    assert result.detected is False
    assert result.per_channel == (False,)


def test_detect_clipping_returns_true_at_positive_threshold() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.5],
                [1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_clipping(audio)

    assert result.detected is True
    assert result.per_channel == (True,)


def test_detect_clipping_returns_true_at_negative_threshold() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.5],
                [-1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_clipping(audio)

    assert result.detected is True
    assert result.per_channel == (True,)


def test_detect_clipping_reports_per_channel_values() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.5, 0.5],
                [0.75, 1.0],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_clipping(audio)

    assert result.detected is True
    assert result.per_channel == (
        False,
        True,
    )


def test_detect_clipping_uses_custom_threshold() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.75],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    result = detect_clipping(
        audio,
        threshold=0.5,
    )

    assert result.detected is True
    assert result.per_channel == (True,)


def test_detect_clipping_rejects_non_positive_threshold() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (1, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        ValueError,
        match="Clipping threshold must be greater than 0",
    ):
        detect_clipping(
            audio,
            threshold=0.0,
        )


def test_detect_clipping_rejects_empty_audio_buffer() -> None:
    audio = AudioBuffer(
        samples=np.empty(
            (0, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        EmptyAudioBufferError,
        match="Clipping detection requires at least one audio frame",
    ):
        detect_clipping(audio)
