from pathlib import Path

import pytest

from audio_hw_framework.configuration.loader import (
    ConfigurationError,
    load_config,
)


def test_load_config() -> None:
    config = load_config(Path("configs/scarlett_2i2.yaml"))

    assert config.device.name_contains == "Scarlett 2i2"

    assert config.stream.sample_rate == 48000


def test_missing_config_file_raises() -> None:
    with pytest.raises(ConfigurationError):
        load_config(Path("does_not_exist.yaml"))


def test_empty_config_raises(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "empty.yaml"

    config_file.write_text(
        "",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError):
        load_config(config_file)


def test_invalid_yaml_raises(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "broken.yaml"

    config_file.write_text(
        "device: [",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError):
        load_config(config_file)
