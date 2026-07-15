from pathlib import Path

import yaml
from pydantic import ValidationError

from audio_hw_framework.device.models import FrameworkConfig


class ConfigurationError(Exception):
    pass


def load_config(path: Path) -> FrameworkConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

        if raw is None:
            raise ConfigurationError("Configuration file is empty")

        return FrameworkConfig.model_validate(raw)

    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {path}") from exc

    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in configuration file: {path}") from exc

    except ValidationError as exc:
        raise ConfigurationError(f"Invalid configuration: {exc}") from exc
