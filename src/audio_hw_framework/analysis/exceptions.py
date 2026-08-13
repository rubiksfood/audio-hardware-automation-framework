"""Exceptions raised by sample-domain audio analysis."""


class AudioAnalysisError(Exception):
    """Base exception for sample-domain audio analysis failures."""


class EmptyAudioBufferError(AudioAnalysisError):
    """Raised when analysis is attempted on an empty audio buffer."""


class InvalidAudioSamplesError(AudioAnalysisError):
    """Raised when audio contains samples unsuitable for analysis."""
