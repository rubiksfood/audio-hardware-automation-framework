"""WAV file reading and writing."""

from pathlib import Path

import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from audio_hw_framework.audio.audio_buffer import AudioBuffer


class WavFileError(RuntimeError):
    """Raised when WAV file I/O fails."""


def read_wav(path: Path) -> AudioBuffer:
    """Read a WAV file into a framework-owned audio buffer."""

    try:
        samples, sample_rate = sf.read(
            path,
            dtype="float32",
            always_2d=True,
        )
    except (sf.SoundFileError, OSError) as exc:
        raise WavFileError(
            f"Could not read WAV file '{path}': {exc}",
        ) from exc

    return AudioBuffer(
        samples=np.asarray(samples, dtype=np.float32),
        sample_rate=int(sample_rate),
    )


def write_wav(
    path: Path,
    audio: AudioBuffer,
) -> None:
    """Write a framework-owned audio buffer as a float32 WAV file."""

    samples = _normalise_to_float32(audio.samples)

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        sf.write(
            path,
            samples,
            audio.sample_rate,
            format="WAV",
            subtype="FLOAT",
        )
    except (sf.SoundFileError, OSError) as exc:
        raise WavFileError(
            f"Could not write WAV file '{path}': {exc}",
        ) from exc


def _normalise_to_float32(
    samples: NDArray[np.generic],
) -> NDArray[np.float32]:
    """Convert numeric audio samples to normalised float32 samples."""

    if np.issubdtype(samples.dtype, np.floating):
        return np.asarray(
            samples,
            dtype=np.float32,
        )

    if np.issubdtype(samples.dtype, np.signedinteger):
        info = np.iinfo(samples.dtype)
        scale = float(max(abs(info.min), info.max))

        return (
            np.asarray(
                samples,
                dtype=np.float32,
            )
            / scale
        )

    if np.issubdtype(samples.dtype, np.unsignedinteger):
        info = np.iinfo(samples.dtype)
        midpoint = float(info.max + 1) / 2.0

        return (
            np.asarray(
                samples,
                dtype=np.float32,
            )
            - midpoint
        ) / midpoint

    raise WavFileError(
        f"Unsupported WAV sample dtype: {samples.dtype}",
    )
