"""Tests for dominant-frequency analysis."""

import numpy as np
import pytest

from audio_hw_framework.analysis import (
    measure_dominant_frequency,
)
from audio_hw_framework.audio import AudioBuffer


def create_sine_wave(
    *,
    frequency_hz: float = 1_000.0,
    sample_rate: int = 48_000,
    duration_seconds: float = 1.0,
    amplitude: float = 0.25,
) -> AudioBuffer:
    """Create deterministic mono sine-wave audio."""

    frame_count = round(
        duration_seconds * sample_rate,
    )

    time_seconds = (
        np.arange(
            frame_count,
            dtype=np.float64,
        )
        / sample_rate
    )

    samples = (amplitude * np.sin(2.0 * np.pi * frequency_hz * time_seconds)).astype(
        np.float32,
    )

    return AudioBuffer(
        samples=samples[:, np.newaxis],
        sample_rate=sample_rate,
    )


def test_measure_dominant_frequency_detects_sine_wave() -> None:
    result = measure_dominant_frequency(
        create_sine_wave(),
    )

    assert result == pytest.approx(
        1_000.0,
        abs=0.1,
    )


def test_measure_dominant_frequency_supports_non_bin_centred_frequency() -> None:
    result = measure_dominant_frequency(
        create_sine_wave(
            frequency_hz=997.5,
        ),
    )

    assert result == pytest.approx(
        997.5,
        abs=0.5,
    )


def test_measure_dominant_frequency_ignores_dc_offset() -> None:
    audio = create_sine_wave()

    samples = np.array(
        audio.samples,
        copy=True,
    )

    samples[:, 0] += 0.2

    result = measure_dominant_frequency(
        AudioBuffer(
            samples=samples,
            sample_rate=audio.sample_rate,
        )
    )

    assert result == pytest.approx(
        1_000.0,
        abs=0.1,
    )


def test_measure_dominant_frequency_returns_zero_for_silence() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (48_000, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    assert measure_dominant_frequency(audio) == 0.0


def test_measure_dominant_frequency_rejects_multichannel_audio() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (100, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        ValueError,
        match="Frequency analysis requires mono audio",
    ):
        measure_dominant_frequency(audio)


def test_measure_dominant_frequency_rejects_too_few_frames() -> None:
    audio = AudioBuffer(
        samples=np.zeros(
            (2, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        ValueError,
        match="Frequency analysis requires at least three frames",
    ):
        measure_dominant_frequency(audio)


def test_measure_dominant_frequency_rejects_non_finite_samples() -> None:
    samples = np.array(
        [
            [0.0],
            [float("nan")],
            [0.1],
        ],
        dtype=np.float32,
    )

    audio = AudioBuffer(
        samples=samples,
        sample_rate=48_000,
    )

    with pytest.raises(
        ValueError,
        match="Frequency analysis requires finite audio samples",
    ):
        measure_dominant_frequency(audio)
