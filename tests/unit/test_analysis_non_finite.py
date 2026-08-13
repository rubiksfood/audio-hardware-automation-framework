import numpy as np
import pytest

from audio_hw_framework.analysis import (
    analyse_dc_offset,
    analyse_peak,
    analyse_rms,
    detect_clipping,
    detect_silence,
)
from audio_hw_framework.analysis.exceptions import InvalidAudioSamplesError
from audio_hw_framework.audio import AudioBuffer


def test_rms_rejects_nan_sample() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0],
                [np.nan],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        InvalidAudioSamplesError,
        match="Audio analysis requires finite sample values",
    ):
        analyse_rms(audio)


def test_peak_rejects_positive_infinity() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0],
                [np.inf],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        InvalidAudioSamplesError,
        match="Audio analysis requires finite sample values",
    ):
        analyse_peak(audio)


def test_dc_offset_rejects_negative_infinity() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0],
                [-np.inf],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        InvalidAudioSamplesError,
        match="Audio analysis requires finite sample values",
    ):
        analyse_dc_offset(audio)


def test_silence_detection_rejects_nan_sample() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0],
                [np.nan],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        InvalidAudioSamplesError,
        match="Audio analysis requires finite sample values",
    ):
        detect_silence(audio)


def test_clipping_detection_rejects_infinite_sample() -> None:
    audio = AudioBuffer(
        samples=np.array(
            [
                [0.0],
                [np.inf],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        InvalidAudioSamplesError,
        match="Audio analysis requires finite sample values",
    ):
        detect_clipping(audio)
