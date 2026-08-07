import numpy as np
import pytest
from numpy.typing import NDArray

from audio_hw_framework.audio import AudioBuffer


def create_samples() -> NDArray[np.float32]:
    return np.array(
        [
            [0.1, -0.1],
            [0.2, -0.2],
            [0.3, -0.3],
        ],
        dtype=np.float32,
    )


def test_audio_buffer_exposes_metadata() -> None:
    buffer = AudioBuffer(
        samples=create_samples(),
        sample_rate=48_000,
    )

    assert buffer.sample_rate == 48_000
    assert buffer.frame_count == 3
    assert buffer.channel_count == 2


def test_audio_buffer_preserves_samples() -> None:
    samples = create_samples()

    buffer = AudioBuffer(
        samples=samples,
        sample_rate=48_000,
    )

    np.testing.assert_array_equal(
        buffer.samples,
        samples,
    )


def test_audio_buffer_owns_sample_data() -> None:
    samples = create_samples()

    buffer = AudioBuffer(
        samples=samples,
        sample_rate=48_000,
    )

    samples[0, 0] = 1.0

    assert buffer.samples[0, 0] == pytest.approx(0.1)


def test_audio_buffer_samples_are_read_only() -> None:
    buffer = AudioBuffer(
        samples=create_samples(),
        sample_rate=48_000,
    )

    with pytest.raises(ValueError):
        buffer.samples[0, 0] = 1.0


def test_audio_buffer_rejects_zero_sample_rate() -> None:
    with pytest.raises(
        ValueError,
        match="sample_rate must be greater than 0",
    ):
        AudioBuffer(
            samples=create_samples(),
            sample_rate=0,
        )


def test_audio_buffer_rejects_negative_sample_rate() -> None:
    with pytest.raises(
        ValueError,
        match="sample_rate must be greater than 0",
    ):
        AudioBuffer(
            samples=create_samples(),
            sample_rate=-1,
        )


def test_audio_buffer_rejects_one_dimensional_samples() -> None:
    samples = np.array(
        [0.1, 0.2, 0.3],
        dtype=np.float32,
    )

    with pytest.raises(
        ValueError,
        match=r"samples must have shape \(frames, channels\)",
    ):
        AudioBuffer(
            samples=samples,
            sample_rate=48_000,
        )


def test_audio_buffer_rejects_more_than_two_dimensions() -> None:
    samples = np.zeros(
        (2, 2, 2),
        dtype=np.float32,
    )

    with pytest.raises(
        ValueError,
        match=r"samples must have shape \(frames, channels\)",
    ):
        AudioBuffer(
            samples=samples,
            sample_rate=48_000,
        )


def test_audio_buffer_rejects_zero_channels() -> None:
    samples = np.empty(
        (3, 0),
        dtype=np.float32,
    )

    with pytest.raises(
        ValueError,
        match="samples must contain at least one channel",
    ):
        AudioBuffer(
            samples=samples,
            sample_rate=48_000,
        )


def test_audio_buffer_accepts_empty_recording() -> None:
    samples = np.empty(
        (0, 2),
        dtype=np.float32,
    )

    buffer = AudioBuffer(
        samples=samples,
        sample_rate=48_000,
    )

    assert buffer.frame_count == 0
    assert buffer.channel_count == 2


def test_audio_buffer_rejects_non_numeric_samples() -> None:
    samples = np.array(
        [["left", "right"]],
    )

    with pytest.raises(
        ValueError,
        match="samples must contain numeric data",
    ):
        AudioBuffer(
            samples=samples,
            sample_rate=48_000,
        )
