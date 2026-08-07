"""Framework-owned representation of decoded audio samples."""

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class AudioBuffer:
    """Immutable framework-owned decoded audio samples."""

    samples: NDArray[np.generic]
    sample_rate: int

    def __post_init__(self) -> None:
        """Validate samples and take immutable ownership of their data."""

        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")

        if self.samples.ndim != 2:
            raise ValueError(
                "samples must have shape (frames, channels)",
            )

        if self.samples.shape[1] == 0:
            raise ValueError("samples must contain at least one channel")

        if not np.issubdtype(self.samples.dtype, np.number):
            raise ValueError("samples must contain numeric data")

        owned_samples: NDArray[Any] = np.array(
            self.samples,
            copy=True,
            order="C",
        )
        owned_samples.setflags(write=False)

        object.__setattr__(
            self,
            "samples",
            owned_samples,
        )

    @property
    def frame_count(self) -> int:
        """Return the number of audio frames."""

        return int(self.samples.shape[0])

    @property
    def channel_count(self) -> int:
        """Return the number of channels per frame."""

        return int(self.samples.shape[1])
