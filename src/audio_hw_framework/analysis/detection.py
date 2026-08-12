"""Sample-domain silence and clipping detection."""

import numpy as np

from audio_hw_framework.analysis._samples import as_finite_float64_samples
from audio_hw_framework.analysis.models import DetectionAnalysisResult
from audio_hw_framework.audio import AudioBuffer

DEFAULT_SILENCE_THRESHOLD = 1e-4
DEFAULT_CLIPPING_THRESHOLD = 1.0


def detect_silence(
    audio: AudioBuffer,
    *,
    threshold: float = DEFAULT_SILENCE_THRESHOLD,
) -> DetectionAnalysisResult:
    """Detect whether audio remains at or below a silence threshold."""

    if audio.frame_count == 0:
        raise ValueError(
            "Silence detection requires at least one audio frame",
        )

    if threshold < 0:
        raise ValueError(
            "Silence threshold must be greater than or equal to 0",
        )

    samples = as_finite_float64_samples(audio)

    absolute_samples = np.abs(samples)

    per_channel_values = np.all(
        absolute_samples <= threshold,
        axis=0,
    )

    detected = bool(
        np.all(per_channel_values),
    )

    return DetectionAnalysisResult(
        detected=detected,
        per_channel=tuple(bool(value) for value in per_channel_values),
    )


def detect_clipping(
    audio: AudioBuffer,
    *,
    threshold: float = DEFAULT_CLIPPING_THRESHOLD,
) -> DetectionAnalysisResult:
    """Detect samples at or above an absolute clipping threshold."""

    if audio.frame_count == 0:
        raise ValueError(
            "Clipping detection requires at least one audio frame",
        )

    if threshold <= 0:
        raise ValueError(
            "Clipping threshold must be greater than 0",
        )

    samples = as_finite_float64_samples(audio)

    absolute_samples = np.abs(samples)

    per_channel_values = np.any(
        absolute_samples >= threshold,
        axis=0,
    )

    detected = bool(
        np.any(per_channel_values),
    )

    return DetectionAnalysisResult(
        detected=detected,
        per_channel=tuple(bool(value) for value in per_channel_values),
    )
