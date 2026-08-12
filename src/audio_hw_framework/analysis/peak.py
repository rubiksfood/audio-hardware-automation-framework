"""Peak sample-domain audio analysis."""

import numpy as np

from audio_hw_framework.analysis._samples import as_finite_float64_samples
from audio_hw_framework.analysis.models import MetricAnalysisResult
from audio_hw_framework.audio import AudioBuffer


def analyse_peak(audio: AudioBuffer) -> MetricAnalysisResult:
    """Calculate overall and per-channel absolute peak levels."""

    if audio.frame_count == 0:
        raise ValueError(
            "Peak analysis requires at least one audio frame",
        )

    samples = as_finite_float64_samples(audio)

    absolute_samples = np.abs(samples)

    per_channel_values = np.max(
        absolute_samples,
        axis=0,
    )

    overall_value = np.max(
        absolute_samples,
    )

    return MetricAnalysisResult(
        overall=float(overall_value),
        per_channel=tuple(float(value) for value in per_channel_values),
    )
