"""Tests for captured-signal alignment."""

import numpy as np
import pytest

from audio_hw_framework.analysis import (
    SignalAlignmentResult,
    align_captured_signal,
)
from audio_hw_framework.audio import AudioBuffer


def create_reference() -> AudioBuffer:
    """Create a deterministic mono reference signal."""

    return AudioBuffer(
        samples=np.array(
            [
                [0.25],
                [-0.5],
                [0.75],
                [-0.25],
            ],
            dtype=np.float32,
        ),
        sample_rate=10,
    )


def create_capture_with_signal(
    *,
    start_frame: int,
    signal: AudioBuffer | None = None,
) -> AudioBuffer:
    """Create a stereo capture containing a signal on input channel 1."""

    reference = signal if signal is not None else create_reference()

    samples = np.zeros(
        (10, 2),
        dtype=np.float32,
    )

    end_frame = start_frame + reference.frame_count

    samples[
        start_frame:end_frame,
        1,
    ] = reference.samples[:, 0]

    return AudioBuffer(
        samples=samples,
        sample_rate=reference.sample_rate,
    )


def test_align_captured_signal_finds_reference() -> None:
    reference = create_reference()

    result = align_captured_signal(
        create_capture_with_signal(
            start_frame=3,
        ),
        reference,
        input_channel=1,
        expected_start_frame=2,
    )

    assert isinstance(
        result,
        SignalAlignmentResult,
    )
    assert result.start_frame == 3
    assert result.offset_frames == 1
    assert result.correlation == pytest.approx(
        1.0,
    )

    np.testing.assert_array_equal(
        result.audio.samples,
        reference.samples,
    )


def test_align_captured_signal_returns_selected_channel_only() -> None:
    reference = create_reference()

    captured_samples = np.zeros(
        (10, 2),
        dtype=np.float32,
    )

    captured_samples[
        3:7,
        0,
    ] = np.array(
        [0.9, 0.9, 0.9, 0.9],
        dtype=np.float32,
    )

    captured_samples[
        3:7,
        1,
    ] = reference.samples[:, 0]

    result = align_captured_signal(
        AudioBuffer(
            samples=captured_samples,
            sample_rate=10,
        ),
        reference,
        input_channel=1,
        expected_start_frame=2,
    )

    assert result.audio.channel_count == 1

    np.testing.assert_array_equal(
        result.audio.samples,
        reference.samples,
    )


def test_align_captured_signal_reports_negative_offset() -> None:
    result = align_captured_signal(
        create_capture_with_signal(
            start_frame=1,
        ),
        create_reference(),
        input_channel=1,
        expected_start_frame=3,
    )

    assert result.start_frame == 1
    assert result.offset_frames == -2


def test_align_captured_signal_supports_inverted_polarity() -> None:
    reference = create_reference()

    inverted_samples = np.negative(
        reference.samples,
        dtype=np.float32,
    )

    inverted = AudioBuffer(
        samples=inverted_samples,
        sample_rate=reference.sample_rate,
    )

    captured = create_capture_with_signal(
        start_frame=3,
        signal=inverted,
    )

    result = align_captured_signal(
        captured,
        reference,
        input_channel=1,
        expected_start_frame=2,
    )

    assert result.start_frame == 3
    assert result.correlation == pytest.approx(
        1.0,
    )

    np.testing.assert_array_equal(
        result.audio.samples,
        inverted.samples,
    )


def test_align_captured_signal_uses_expected_start_for_silence() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (10, 2),
            dtype=np.float32,
        ),
        sample_rate=10,
    )

    result = align_captured_signal(
        captured,
        create_reference(),
        input_channel=1,
        expected_start_frame=3,
    )

    assert result.start_frame == 3
    assert result.offset_frames == 0
    assert result.correlation == 0.0
    assert result.audio.frame_count == 4

    np.testing.assert_array_equal(
        result.audio.samples,
        np.zeros(
            (4, 1),
            dtype=np.float32,
        ),
    )


def test_align_captured_signal_ignores_dc_offset() -> None:
    reference = create_reference()

    captured = create_capture_with_signal(
        start_frame=3,
    )

    samples = np.array(
        captured.samples,
        copy=True,
    )
    samples[:, 1] += 0.5

    result = align_captured_signal(
        AudioBuffer(
            samples=samples,
            sample_rate=captured.sample_rate,
        ),
        reference,
        input_channel=1,
        expected_start_frame=2,
    )

    assert result.start_frame == 3
    assert result.correlation == pytest.approx(
        1.0,
    )


def test_align_captured_signal_returns_framework_owned_audio() -> None:
    captured = create_capture_with_signal(
        start_frame=3,
    )

    result = align_captured_signal(
        captured,
        create_reference(),
        input_channel=1,
        expected_start_frame=2,
    )

    assert result.audio is not captured
    assert result.audio.sample_rate == captured.sample_rate
    assert not result.audio.samples.flags.writeable


def test_align_captured_signal_rejects_multichannel_reference() -> None:
    reference = AudioBuffer(
        samples=np.zeros(
            (4, 2),
            dtype=np.float32,
        ),
        sample_rate=10,
    )

    with pytest.raises(
        ValueError,
        match="Signal alignment requires mono reference audio",
    ):
        align_captured_signal(
            create_capture_with_signal(
                start_frame=3,
            ),
            reference,
            input_channel=1,
            expected_start_frame=2,
        )


def test_align_captured_signal_rejects_empty_reference() -> None:
    reference = AudioBuffer(
        samples=np.empty(
            (0, 1),
            dtype=np.float32,
        ),
        sample_rate=10,
    )

    captured = AudioBuffer(
        samples=np.zeros(
            (10, 2),
            dtype=np.float32,
        ),
        sample_rate=10,
    )

    with pytest.raises(
        ValueError,
        match="Reference audio must contain at least one frame",
    ):
        align_captured_signal(
            captured,
            reference,
            input_channel=1,
            expected_start_frame=2,
        )


def test_align_captured_signal_rejects_constant_reference() -> None:
    reference = AudioBuffer(
        samples=np.ones(
            (4, 1),
            dtype=np.float32,
        ),
        sample_rate=10,
    )

    with pytest.raises(
        ValueError,
        match="Reference audio must contain a non-constant signal",
    ):
        align_captured_signal(
            create_capture_with_signal(
                start_frame=3,
            ),
            reference,
            input_channel=1,
            expected_start_frame=2,
        )


def test_align_captured_signal_rejects_sample_rate_mismatch() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (10, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        ValueError,
        match="Captured and reference audio sample rates must match",
    ):
        align_captured_signal(
            captured,
            create_reference(),
            input_channel=1,
            expected_start_frame=2,
        )


def test_align_captured_signal_rejects_negative_input_channel() -> None:
    with pytest.raises(
        ValueError,
        match="input_channel must be greater than or equal to 0",
    ):
        align_captured_signal(
            create_capture_with_signal(
                start_frame=3,
            ),
            create_reference(),
            input_channel=-1,
            expected_start_frame=2,
        )


def test_align_captured_signal_rejects_out_of_range_input_channel() -> None:
    with pytest.raises(
        ValueError,
        match="input_channel must be less than the captured channel count",
    ):
        align_captured_signal(
            create_capture_with_signal(
                start_frame=3,
            ),
            create_reference(),
            input_channel=2,
            expected_start_frame=2,
        )


def test_align_captured_signal_rejects_capture_shorter_than_reference() -> None:
    captured = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=10,
    )

    with pytest.raises(
        ValueError,
        match=("Captured audio must contain at least as many frames as the reference audio"),
    ):
        align_captured_signal(
            captured,
            create_reference(),
            input_channel=1,
            expected_start_frame=0,
        )


def test_align_captured_signal_rejects_negative_expected_start() -> None:
    with pytest.raises(
        ValueError,
        match="expected_start_frame must be greater than or equal to 0",
    ):
        align_captured_signal(
            create_capture_with_signal(
                start_frame=3,
            ),
            create_reference(),
            input_channel=1,
            expected_start_frame=-1,
        )


def test_align_captured_signal_rejects_expected_start_too_late() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expected_start_frame does not leave enough captured audio for the reference signal"
        ),
    ):
        align_captured_signal(
            create_capture_with_signal(
                start_frame=3,
            ),
            create_reference(),
            input_channel=1,
            expected_start_frame=7,
        )
