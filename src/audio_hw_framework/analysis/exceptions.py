"""Exceptions raised by sample-domain audio analysis."""


class AudioAnalysisError(Exception):
    """Base exception for sample-domain audio analysis failures."""


class EmptyAudioBufferError(AudioAnalysisError):
    """Raised when analysis is attempted on an empty audio buffer."""
