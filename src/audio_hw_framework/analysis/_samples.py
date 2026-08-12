"""Shared sample preparation for audio analysis."""

import numpy as np
from numpy.typing import NDArray

from audio_hw_framework.audio import AudioBuffer


def as_finite_float64_samples(
    audio: AudioBuffer,
) -> NDArray[np.float64]:
    """Return analysis samples as float64 and reject non-finite values."""

    samples: NDArray[np.float64] = np.asarray(
        audio.samples,
        dtype=np.float64,
    )

    if not bool(
        np.all(
            np.isfinite(samples),
        )
    ):
        raise ValueError(
            "Audio analysis requires finite sample values",
        )

    return samples
