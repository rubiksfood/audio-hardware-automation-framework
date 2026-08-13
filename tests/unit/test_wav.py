from pathlib import Path

import numpy as np
import pytest

from audio_hw_framework.audio import (
    AudioBuffer,
    WavFileError,
    read_wav,
    write_wav,
)


def test_writes_and_reads_float32_wav(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test.wav"

    audio = AudioBuffer(
        samples=np.array(
            [
                [0.1, -0.1],
                [0.2, -0.2],
                [0.3, -0.3],
            ],
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    write_wav(path, audio)

    result = read_wav(path)

    assert path.is_file()
    assert result.sample_rate == 48_000
    assert result.frame_count == 3
    assert result.channel_count == 2
    assert result.samples.dtype == np.float32

    np.testing.assert_allclose(
        np.asarray(result.samples, dtype=np.float32),
        np.asarray(audio.samples, dtype=np.float32),
    )


def test_reads_mono_wav_as_two_dimensional_buffer(
    tmp_path: Path,
) -> None:
    path = tmp_path / "mono.wav"

    audio = AudioBuffer(
        samples=np.array(
            [
                [0.1],
                [0.2],
                [0.3],
            ],
            dtype=np.float32,
        ),
        sample_rate=44_100,
    )

    write_wav(path, audio)

    result = read_wav(path)

    assert result.samples.shape == (3, 1)
    assert result.channel_count == 1


def test_normalises_integer_samples_when_writing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "integer.wav"

    audio = AudioBuffer(
        samples=np.array(
            [
                [-32_768],
                [0],
                [32_767],
            ],
            dtype=np.int16,
        ),
        sample_rate=48_000,
    )

    write_wav(path, audio)

    result = read_wav(path)

    assert result.samples.dtype == np.float32

    np.testing.assert_allclose(
        np.asarray(result.samples[:, 0], dtype=np.float32),
        np.array(
            [
                -1.0,
                0.0,
                32_767 / 32_768,
            ],
            dtype=np.float32,
        ),
    )


def test_normalises_unsigned_integer_samples_when_writing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "unsigned.wav"

    audio = AudioBuffer(
        samples=np.array(
            [
                [0],
                [128],
                [255],
            ],
            dtype=np.uint8,
        ),
        sample_rate=48_000,
    )

    write_wav(path, audio)

    result = read_wav(path)

    np.testing.assert_allclose(
        np.asarray(result.samples[:, 0], dtype=np.float32),
        np.array(
            [
                -1.0,
                0.0,
                127 / 128,
            ],
            dtype=np.float32,
        ),
    )


def test_normalises_int8_samples_when_writing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "int8.wav"

    audio = AudioBuffer(
        samples=np.array(
            [
                [-128],
                [0],
                [127],
            ],
            dtype=np.int8,
        ),
        sample_rate=48_000,
    )

    write_wav(path, audio)

    result = read_wav(path)

    np.testing.assert_allclose(
        np.asarray(result.samples[:, 0], dtype=np.float32),
        np.array(
            [
                -1.0,
                0.0,
                127 / 128,
            ],
            dtype=np.float32,
        ),
    )


def test_normalises_int32_samples_when_writing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "int32.wav"

    audio = AudioBuffer(
        samples=np.array(
            [
                [-2_147_483_648],
                [0],
                [2_147_483_647],
            ],
            dtype=np.int32,
        ),
        sample_rate=48_000,
    )

    write_wav(path, audio)

    result = read_wav(path)

    np.testing.assert_allclose(
        np.asarray(result.samples[:, 0], dtype=np.float32),
        np.array(
            [
                -1.0,
                0.0,
                2_147_483_647 / 2_147_483_648,
            ],
            dtype=np.float32,
        ),
    )


def test_write_wav_creates_parent_directories(
    tmp_path: Path,
) -> None:
    path = tmp_path / "recordings" / "session" / "test.wav"

    audio = AudioBuffer(
        samples=np.zeros(
            (3, 2),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    write_wav(path, audio)

    assert path.is_file()


def test_read_wav_translates_file_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing.wav"

    with pytest.raises(
        WavFileError,
        match="Could not read WAV file",
    ):
        read_wav(path)


def test_read_wav_rejects_invalid_audio_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "invalid.wav"
    path.write_text(
        "not a WAV file",
        encoding="utf-8",
    )

    with pytest.raises(
        WavFileError,
        match="Could not read WAV file",
    ):
        read_wav(path)


def test_write_wav_rejects_unsupported_sample_dtype(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test.wav"

    audio = AudioBuffer(
        samples=np.array(
            [
                [1.0 + 1.0j],
            ],
            dtype=np.complex64,
        ),
        sample_rate=48_000,
    )

    with pytest.raises(
        WavFileError,
        match="Unsupported WAV sample dtype",
    ):
        write_wav(path, audio)


def test_write_wav_translates_file_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "test.wav"

    audio = AudioBuffer(
        samples=np.zeros(
            (1, 1),
            dtype=np.float32,
        ),
        sample_rate=48_000,
    )

    def fail_write(
        *args: object,
        **kwargs: object,
    ) -> None:
        raise OSError("Disk write failed")

    monkeypatch.setattr(
        "audio_hw_framework.audio.wav.sf.write",
        fail_write,
    )

    with pytest.raises(
        WavFileError,
        match="Could not write WAV file",
    ):
        write_wav(path, audio)
