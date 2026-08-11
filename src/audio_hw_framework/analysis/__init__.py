"""Sample-domain audio analysis."""

from audio_hw_framework.analysis.dc_offset import analyse_dc_offset
from audio_hw_framework.analysis.detection import (
    DEFAULT_CLIPPING_THRESHOLD,
    DEFAULT_SILENCE_THRESHOLD,
    detect_clipping,
    detect_silence,
)
from audio_hw_framework.analysis.models import (
    DetectionAnalysisResult,
    MetricAnalysisResult,
)
from audio_hw_framework.analysis.peak import analyse_peak
from audio_hw_framework.analysis.rms import analyse_rms

__all__ = [
    "DEFAULT_CLIPPING_THRESHOLD",
    "DEFAULT_SILENCE_THRESHOLD",
    "DetectionAnalysisResult",
    "MetricAnalysisResult",
    "analyse_dc_offset",
    "analyse_peak",
    "analyse_rms",
    "detect_clipping",
    "detect_silence",
]
