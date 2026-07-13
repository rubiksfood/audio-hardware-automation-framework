# Audio Hardware Automation Framework

A cross-platform Python and pytest framework for repeatable audio-hardware discovery, configuration validation and, in later phases, playback, recording, loopback and reliability testing.

## Current status

Phase 1: device discovery and configuration.

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
```

---