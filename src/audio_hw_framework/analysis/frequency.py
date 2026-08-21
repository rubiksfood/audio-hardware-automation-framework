"""Dominant-frequency analysis for captured audio."""

import numpy as np

from audio_hw_framework.audio import AudioBuffer


def measure_dominant_frequency(
    audio: AudioBuffer,
) -> float:
    """Measure the dominant non-DC frequency of mono audio."""

    if audio.channel_count != 1:
        raise ValueError(
            "Frequency analysis requires mono audio",
        )

    if audio.frame_count < 3:
        raise ValueError(
            "Frequency analysis requires at least three frames",
        )

    samples = np.asarray(
        audio.samples[:, 0],
        dtype=np.float64,
    )

    if not np.all(np.isfinite(samples)):
        raise ValueError(
            "Frequency analysis requires finite audio samples",
        )

    centred_samples = samples - np.mean(samples)

    if not np.any(centred_samples):
        return 0.0

    window = np.hanning(
        audio.frame_count,
    )

    windowed_samples = centred_samples * window

    magnitudes = np.abs(
        np.fft.rfft(
            windowed_samples,
        )
    )

    magnitudes[0] = 0.0

    peak_bin = int(np.argmax(magnitudes))

    bin_offset = _interpolate_peak_bin(
        magnitudes,
        peak_bin,
    )

    return (peak_bin + bin_offset) * audio.sample_rate / audio.frame_count


def _interpolate_peak_bin(
    magnitudes: np.ndarray,
    peak_bin: int,
) -> float:
    """Estimate the sub-bin offset of an FFT magnitude peak."""

    if peak_bin <= 0 or peak_bin >= magnitudes.size - 1:
        return 0.0

    left = float(magnitudes[peak_bin - 1])
    centre = float(magnitudes[peak_bin])
    right = float(magnitudes[peak_bin + 1])

    denominator = left - (2.0 * centre) + right

    if denominator == 0.0:
        return 0.0

    offset = 0.5 * (left - right) / denominator

    return float(
        np.clip(
            offset,
            -0.5,
            0.5,
        )
    )
