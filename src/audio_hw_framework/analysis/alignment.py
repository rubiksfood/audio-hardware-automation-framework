"""Captured-signal alignment for loopback analysis."""

from dataclasses import dataclass

import numpy as np

from audio_hw_framework.audio import AudioBuffer


@dataclass(frozen=True, slots=True)
class SignalAlignmentResult:
    """Result of locating a reference signal within captured audio."""

    audio: AudioBuffer
    start_frame: int
    offset_frames: int
    correlation: float


def align_captured_signal(
    captured: AudioBuffer,
    reference: AudioBuffer,
    *,
    input_channel: int,
    expected_start_frame: int,
) -> SignalAlignmentResult:
    """Align one captured input channel to a known mono reference signal."""

    if reference.channel_count != 1:
        raise ValueError("Signal alignment requires mono reference audio")

    if reference.frame_count == 0:
        raise ValueError("Reference audio must contain at least one frame")

    if captured.sample_rate != reference.sample_rate:
        raise ValueError(
            "Captured and reference audio sample rates must match",
        )

    if input_channel < 0:
        raise ValueError(
            "input_channel must be greater than or equal to 0",
        )

    if input_channel >= captured.channel_count:
        raise ValueError(
            "input_channel must be less than the captured channel count",
        )

    if captured.frame_count < reference.frame_count:
        raise ValueError(
            "Captured audio must contain at least as many frames as the reference audio",
        )

    maximum_start_frame = captured.frame_count - reference.frame_count

    if expected_start_frame < 0:
        raise ValueError(
            "expected_start_frame must be greater than or equal to 0",
        )

    if expected_start_frame > maximum_start_frame:
        raise ValueError(
            "expected_start_frame does not leave enough captured audio for the reference signal",
        )

    captured_samples = np.asarray(
        captured.samples[:, input_channel],
        dtype=np.float64,
    )

    reference_samples = np.asarray(
        reference.samples[:, 0],
        dtype=np.float64,
    )

    centred_reference = reference_samples - np.mean(
        reference_samples,
    )

    reference_energy = float(
        np.dot(
            centred_reference,
            centred_reference,
        )
    )

    if reference_energy == 0.0:
        raise ValueError(
            "Reference audio must contain a non-constant signal",
        )

    correlations = _valid_cross_correlation(
        captured_samples,
        centred_reference,
    )

    window_energies = _sliding_window_centred_energy(
        captured_samples,
        reference.frame_count,
    )

    denominators = np.sqrt(
        window_energies * reference_energy,
    )

    scores = np.zeros_like(
        correlations,
        dtype=np.float64,
    )

    np.divide(
        np.abs(correlations),
        denominators,
        out=scores,
        where=denominators > 0.0,
    )

    np.clip(
        scores,
        0.0,
        1.0,
        out=scores,
    )

    best_score = float(np.max(scores))

    candidate_frames = np.flatnonzero(
        np.isclose(
            scores,
            best_score,
            rtol=1e-12,
            atol=1e-12,
        )
    )

    distances = np.abs(
        candidate_frames - expected_start_frame,
    )

    start_frame = int(candidate_frames[np.argmin(distances)])

    end_frame = start_frame + reference.frame_count

    aligned_audio = AudioBuffer(
        samples=captured.samples[
            start_frame:end_frame,
            input_channel : input_channel + 1,
        ],
        sample_rate=captured.sample_rate,
    )

    return SignalAlignmentResult(
        audio=aligned_audio,
        start_frame=start_frame,
        offset_frames=start_frame - expected_start_frame,
        correlation=float(scores[start_frame]),
    )


def _valid_cross_correlation(
    captured: np.ndarray,
    reference: np.ndarray,
) -> np.ndarray:
    """Return correlation values for all full-reference capture windows."""

    full_length = captured.size + reference.size - 1

    fft_length = 1 << (full_length - 1).bit_length()

    captured_spectrum = np.fft.rfft(
        captured,
        n=fft_length,
    )
    reference_spectrum = np.fft.rfft(
        reference[::-1],
        n=fft_length,
    )

    convolution = np.fft.irfft(
        captured_spectrum * reference_spectrum,
        n=fft_length,
    )

    valid_start = reference.size - 1
    valid_end = captured.size

    return convolution[valid_start:valid_end]


def _sliding_window_centred_energy(
    samples: np.ndarray,
    window_size: int,
) -> np.ndarray:
    """Return centred energy for every complete sliding window."""

    cumulative_sum = np.concatenate((
        np.zeros(
            1,
            dtype=np.float64,
        ),
        np.cumsum(
            samples,
            dtype=np.float64,
        ),
    ))

    squared_samples = np.square(
        samples,
        dtype=np.float64,
    )

    cumulative_squared_sum = np.concatenate((
        np.zeros(
            1,
            dtype=np.float64,
        ),
        np.cumsum(
            squared_samples,
            dtype=np.float64,
        ),
    ))

    window_sums = cumulative_sum[window_size:] - cumulative_sum[:-window_size]

    window_squared_sums = (
        cumulative_squared_sum[window_size:] - cumulative_squared_sum[:-window_size]
    )

    centred_energy = window_squared_sums - np.square(window_sums) / window_size

    return np.maximum(
        centred_energy,
        0.0,
    )
